# Repository Instructions

Keep this package local-first and dependency-free at runtime.
Use the existing Config, Store and runner boundaries rather than adding an agent
framework. Preserve attempt history and validate metric/evidence contracts.

Run `python -m pytest`, `ruff check .`, and `ruff format --check .` for changes.
Run the packaged offline demo when touching templates, entry points or packaging.
Use synthetic fixtures only. Do not include generated workspaces, local logs,
credentials, private data, machine paths or organization-specific integrations.

Do not describe deterministic contract validation as scientific verification,
independent model review, or a sandbox. Never silently retry experiments,
rewrite old results, upload submissions or raise resource budgets.
