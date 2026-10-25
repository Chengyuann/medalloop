# Configuration and Output Contract

## Plan

`loop.json` is strict JSON. Duplicate keys, non-finite JSON numbers and unknown
configuration fields are rejected. JSON object key order and whitespace do not
affect the configuration fingerprint. List order does.

| Field | Required | Meaning |
| --- | --- | --- |
| `name` | Yes | Human-readable experiment round. |
| `metric.name` | Yes | Exact primary metric name. |
| `metric.direction` | Yes | `maximize` or `minimize`. |
| `evaluation_id` | Yes | User-owned identifier for dataset/split/metric protocol. |
| `tasks` | Yes | Nonempty ordered list of tasks. |
| `budget` | No | Operational limits below. |

Use an evaluation ID that includes your dataset version, split policy and other
important protocol details. Matching IDs are a contract, not an automatic check
that the underlying data or code is identical.

## Budget

| Field | Default | Scope |
| --- | ---: | --- |
| `max_steps` | 10 | Total attempts across the workspace, including retries and failures. |
| `max_failures` | 2 | Consecutive failed/interrupted attempts before normal scheduling stops. |
| `patience` | 3 | Verified successes without improvement after the retained result. |
| `min_delta` | 0 | Strict directional improvement threshold. |
| `timeout` | 300 | Seconds allowed for one command. |
| `max_wall_seconds` | 3600 | Accumulated attempt duration, including failed attempts. |

Counts must be positive integers. Durations must be finite and positive.
`min_delta` must be finite and nonnegative.

`run --steps N` caps this invocation, without resetting workspace limits.
The remaining wall-time budget also limits each command. Process startup,
verification, SQLite writes and process cleanup are not hard real-time operations;
small overruns are possible. Waiting between invocations is not charged for
completed attempts.

An orphaned attempt's recovery duration is conservatively estimated from its
start timestamp until recovery. This can include operator downtime.

## Tasks

Each task has `id`, `hypothesis`, `command`, optional `metrics` (default
`metrics.json`) and optional `artifacts` (default `[]`).

IDs are unique, 1-64 ASCII letters/digits/underscores/hyphens, starting with a letter
or digit. Commands are argv arrays. `{python}` is the only special argument.
There is no shell expansion, pipeline parsing, templating or automatic install.

Artifact and metrics paths are relative to the attempt directory. Absolute paths,
parent traversal, Windows drives, backslashes, output collisions and resolved
paths outside that directory are rejected.

`stdout.log`, `stderr.log` and `provenance.json` are reserved.

## Metrics

```json
{
  "metric": {"name": "mse", "value": 0.25},
  "evaluation_id": "my-fixed-protocol"
}
```

`metric.value` must be a finite JSON number, not a string or boolean. The metric
name and evaluation ID must exactly match the plan. Additional evaluator fields
are permitted but do not change the decision policy.

Every declared artifact must be a regular readable file. Existence and hashing do
not check its task-specific semantics. Add assertions to the evaluator for such
constraints as row counts, output schema and leakage-safe feature construction.

## Failure and Retry

- Nonzero exit, timeout or rejected output records a failed attempt.
- A caught operator interruption records an interrupted attempt and exits 130.
- A hard-killed runner leaves a running row, reconciled on the next run.
- `run` never automatically repeats an attempted task.
- `retry TASK --execute` creates one new attempt only for a failed/interrupted task.
- Explicit retry bypasses patience/failure circuits for that one task, **not**
  cumulative attempt or wall-time budgets.
- Healthy rejection is not a failure and cannot be retried with `retry`.

All config changes after execution starts require a fresh workspace. Do not edit
the ledger to reset the limits. Preserve the old round as a record.

## Exit Codes

| Code | Meaning |
| --- | --- |
| 0 | Command succeeded. Budget/patience stopping may be normal. |
| 1 | Validation failed, evidence invalid, or latest task attempts include unresolved failures. |
| 2 | Invalid configuration, refused operation or filesystem/database error. |
| 130 | Operator interruption caught by the runner. |

A later successful explicit retry resolves that task's current failure status.
Old failed attempts remain in history. Inspect `stop_reason` and `history` rather
than treating exit code 0 as a claim that every planned task executed.
