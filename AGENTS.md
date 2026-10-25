# Repository Instructions

MedalLoop is an Agent iteration framework for machine-learning competitions.
Keep competition research, CV, algorithm experiments, OOF/ensembles, submission
feedback and multi-round learning central to the product and documentation.
Keep the deterministic runner local-first and dependency-free at runtime.
Preserve attempt history and validate metric/evidence contracts.

Run `python -m pytest`, `ruff check .`, and `ruff format --check .` for changes.
Run the packaged offline demo when touching templates, entry points or packaging.
Use synthetic fixtures only. Do not include generated workspaces, local logs,
credentials, private data, machine paths or organization-specific integrations.

Do not describe deterministic contract validation as scientific verification,
independent model review, or a sandbox. Never silently retry experiments,
rewrite old results, upload submissions or raise resource budgets.
