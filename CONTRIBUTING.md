# Contributing

MedalLoop is an Agent iteration framework for machine-learning competitions.
Contributions should improve the actual competition workflow: validation,
controlled experiments, error analysis, campaign memory, OOF analysis, ensembles,
submission checks and reproducible final solutions.

Keep the deterministic runner lightweight. Optional model or platform integrations
should not force every user to install a provider SDK or sign up for a cloud service.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
ruff check .
ruff format --check .
```

## A Useful Pull Request

1. Describe the failure or user need and the smallest relevant example.
2. Change one behavior where possible.
3. Add a regression test for a bug and failure-path tests for new execution behavior.
4. Update documentation when CLI semantics or the output contract changes.
5. Run the offline demo and packaging checks when changing package resources.

Do not include datasets, credentials, private endpoints, personal paths, local
ledgers, model outputs from private tasks, or unredacted logs. Use synthetic
fixtures. Do not weaken validation merely to make a test or example succeed.

## Design Boundaries

- Keep planning separate from deterministic checking.
- Preserve failed attempts; never silently repair a reported metric.
- Require explicit operator action for execution and retries.
- Do not introduce automatic remote writes or submission behavior.
- Discuss schema changes before implementation. There is no stable migration
  promise during the 0.x series.

## Reporting Problems

Use a GitHub issue for ordinary bugs. Include the Python version, operating
system, minimal plan and expected behavior. Inspect all pasted output for secrets.
For security issues, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.
