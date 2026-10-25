# Competition Workflow

MedalLoop separates a long-running competition campaign from an individual
experiment round.

## Campaign

The campaign is the full competition project:

```text
COMPETITION.md
memory/STATE.md
memory/HYPOTHESES.md
memory/RESULTS.md
rounds/001/
rounds/002/
...
```

The coding agent updates campaign memory after reviewing actual outputs.
The CLI does not edit these documents or fetch leaderboard results.

`STATE.md` answers: What is the current best reviewed solution? Which round is
active? What is the next action? What is still running or blocked?

`HYPOTHESES.md` prevents random trial accumulation. Each idea needs a supporting
observation and an estimate of expected gain, cost and information value.

`RESULTS.md` separates local evaluation from official submissions. An official
score needs a platform response or operator-provided source and the exact file hash.

## Round

A round is a controlled comparison under one configuration identity:

```text
rounds/001/
  loop.json
  train.py
  baseline.json
  candidate.json
  ledger.sqlite3
  runs/
```

All tasks in a round must use the same primary metric and evaluation protocol.
After the first attempt, `loop.json` is immutable. This prevents the reference
score from silently changing underneath later experiments.

The first verified task establishes the round reference. Later tasks must exceed
it by more than `min_delta` in the configured direction to become the retained
result. Rejected successful experiments remain available for analysis and ensembles.

## Moving to the Next Round

Create a new round when:

- changing the dataset version or folds;
- redesigning the metric/evaluator;
- replacing the candidate set after a completed or stagnant round;
- performing a distinct ablation or stability study.

The old round remains an immutable comparison record. Begin the new round by
re-running the campaign's previous best implementation as the reference. A new
SQLite ledger does not automatically know the previous champion.

## CV and Leaderboard Feedback

Local CV should drive most algorithm iteration because it is repeatable and
supports fold/error-slice analysis. Official leaderboard feedback is valuable
but scarce and can encourage public-leaderboard overfitting.

Record separately:

- local CV value, per-fold values and evaluation ID;
- the exact generated submission and its hash;
- official public/private score and timestamp;
- whether the result supports or contradicts local validation.

Do not silently substitute a leaderboard score into the runner's local metric.

## OOF and Ensembles

For meaningful ensemble analysis, store OOF predictions with stable row IDs and
fold assignments. Compare correlation or residual complementarity only when
predictions cover the same examples under the same evaluation protocol.

The CLI's `blend` command performs strict ID-set alignment and refuses to overwrite
an existing output. It does not select weights or prove that a blend generalizes.

## Failure and Recovery

Every attempt becomes succeeded, failed or interrupted. A normal run does not
repeat an attempted task. `retry TASK` is valid only for a failed/interrupted task
and creates a new numbered attempt.

On restart, an uncommitted running row becomes interrupted. This protects the
ledger, but does not prove that an uncatchable old process has stopped. Inspect
the machine before an explicit retry.

## Deadline Mode

As the deadline approaches, stop broad research and prioritize:

1. reproducible inference from the reviewed best models;
2. submission schema and ID validation;
3. ensemble reconstruction from preserved OOF/test predictions;
4. dependency/configuration freeze;
5. final runbook and file hashes;
6. one operator-authorized submission path.

Late experiments belong in a new round and should not replace a stable solution
without completing the same validation and packaging checks.
