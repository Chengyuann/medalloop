# Integrating a Coding Agent

An agent does not need a dedicated SDK integration. It can invoke the CLI as a
local tool and consume JSON output. The same commands also work for a human.

## Responsibilities

| Role | Owner | Output |
| --- | --- | --- |
| Propose | Human or coding agent | Hypothesis and bounded task plan. |
| Review | Human or an explicitly configured reviewer | Split, data rights, metric and command review. |
| Execute | Evidence Loop | Isolated attempt directories and subprocess logs. |
| Check | Evidence Loop plus task-specific evaluator | Output contract, hashes and explicit assertions. |
| Interpret | Human or coding agent | Evidence-grounded summary and next-round proposal. |

Directory isolation is not process isolation. The deterministic checks are not
an independent scientific reviewer.

## Tool Protocol

1. Create a fresh workspace with `init`.
2. Prepare `loop.json` and evaluator files.
3. Read `plan` and review the actual command arguments.
4. Execute only with the operator's authorization.
5. Inspect JSON `stop_reason`, per-attempt `state`, `decision` and `reason`.
6. Run `verify` and inspect artifacts before reporting conclusions.
7. Propose the next round in a new workspace; do not mutate a completed round.

## Suggested Instruction

```text
Use Evidence Loop for local experiment execution.
Do not invent scores or repair invalid output after the fact.
Keep evaluation identity stable and preserve each attempt.
Separate implementation, numerical validation and scientific interpretation.
Treat a process exit as execution evidence, not evidence of improvement.
Do not bypass budget stops, rerun failed tasks or publish artifacts without approval.
Never paste secrets, private datasets or unredacted logs into reports.
```

## Adapting Existing Training Code

Use `EVIDENCE_LOOP_RUN_DIR` as the output directory. Write the metrics envelope
only after evaluation finishes. Record useful artifacts such as the resolved
configuration, split IDs or dataset hashes, dependency versions, predictions and
per-seed scores. Only list artifacts you actually produce.

If a training script needs a model API, credentials stay in the runtime
environment. This project does not provide provider adapters or manage model
spending. Add explicit cost controls in the calling application.

## Before a Real Competition

Review allowed datasets, external model rules, submission limits and evaluation
policy independently. Maintain a genuinely held-out final check; repeated
experiments on one holdout can overfit it. A synthetic demo cannot establish
expected leaderboard gains.
