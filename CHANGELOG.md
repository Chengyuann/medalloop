# Changelog

## 0.2.0 - 2026-10-25

- Renamed the project and Python package to MedalLoop, focused on ML competition iteration.
- Added `medalloop init --competition` with a complete competition Agent workflow,
  task brief, campaign state, hypothesis backlog, CV/submission history and first-round plan.
- Rewrote English and Chinese documentation around baseline, controlled experiments,
  error analysis, OOF/ensembles, leaderboard feedback and next-round decisions.
- Replaced generic artwork with a competition-specific cover and workflow diagram.
- Kept the `evidence-loop` executable, legacy output environment variables and lock
  filename for existing scripts and workspace compatibility.

## 0.1.0 - 2026-10-25

First public release.

- Added real bounded command execution and persistent attempt state.
- Added configuration identity, protocol-aware metric checks and artifact manifests.
- Added explicit retry and interruption recovery with failure retention.
- Added patience, failure, attempt and wall-time stopping conditions.
- Added strict CSV validation, aligned mean blending and tie-aware rank blending.
- Added an offline synthetic demo, installable CLI, tests and CI.
- Replaced machine-specific material with generic documentation and synthetic examples.

No prior competition results or claims of score improvement are part of this release.
