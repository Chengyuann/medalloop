# MedalLoop Offline Demo

This is a small execution demo, not a competition solution. For a real competition,
run `medalloop init my-competition --competition` and follow that project's AGENTS.md.

Review loop.json before executing. Run `medalloop run --execute`, then
`medalloop report` and `medalloop verify`. The demo uses a fixed synthetic holdout.
It establishes a baseline, tests a linear fit and intercept adjustment, then stops
after two successful experiments without improvement.

Write outputs to MEDALLOOP_RUN_DIR. Keep the metric and evaluation_id unchanged.
Do not rewrite existing results, silently retry a failure or raise limits.
Commands execute locally with the operator's permissions; this is not a sandbox.
