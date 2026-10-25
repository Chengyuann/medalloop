# Experiment Workspace

Before proposing work, read loop.json and run `evidence-loop status`.
Write one explicit hypothesis per task. Keep the metric, split, seed and data
version fixed within an evaluation protocol. Do not compare unrelated scores.

Commands run locally with the operator's permissions. Never execute downloaded
or generated code without review. Do not print credentials into logs.

Write metrics and artifacts only to EVIDENCE_LOOP_RUN_DIR. Use the metric
envelope documented in the repository. The runner decides whether the recorded
result improves on the current reference; never claim a result from prose alone.

Do not edit the SQLite ledger or old artifacts. Use a new workspace when changing
the protocol. Failed attempts require an explicit `retry` command. Stop when the
runner reports a budget or patience limit; do not raise limits without approval.

Review data leakage, dataset permissions and evaluation validity separately.
A successful process and matching hashes do not establish scientific validity.
Never upload submissions, publish data or modify remote systems automatically.
