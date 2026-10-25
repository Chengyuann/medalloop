from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from importlib import resources
from pathlib import Path

from . import __version__
from .config import LoopError, load_config
from .runner import audit_evidence, run, status
from .submission import blend, check_submission


def initialize(root: Path, competition: bool = False) -> dict:
    if root.exists():
        raise LoopError("destination already exists; choose a new workspace")
    root.mkdir(parents=True)
    try:
        templates = resources.files("medalloop").joinpath("templates")
        if competition:
            files = {
                "competition-agent.md": "AGENTS.md",
                "competition-brief.md": "COMPETITION.md",
                "competition-state.md": "memory/STATE.md",
                "competition-ideas.md": "memory/HYPOTHESES.md",
                "competition-results.md": "memory/RESULTS.md",
                "competition-plan.json": "rounds/001/loop.json",
                "competition-round.md": "rounds/001/README.md",
                ".gitignore": ".gitignore",
            }
        else:
            files = {
                name: name for name in ("loop.json", "experiment.py", "AGENTS.md", ".gitignore")
            }
        for source_name, destination in files.items():
            source = templates.joinpath(source_name)
            target = root / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    except Exception:
        shutil.rmtree(root)
        raise
    return {
        "ok": True,
        "workspace": str(root),
        "mode": "competition" if competition else "demo",
        "next": (
            "Complete COMPETITION.md, then give AGENTS.md to your coding agent. "
            "The first round needs your training script and evaluation protocol."
            if competition
            else "review loop.json, then run --execute"
        ),
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="medalloop",
        description="Iterate on ML competition solutions: baseline, experiment, evaluate, ensemble.",
    )
    p.add_argument("--version", action="version", version=__version__)
    commands = p.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create a competition project or offline demo")
    init.add_argument("path", type=Path)
    init.add_argument(
        "--competition",
        action="store_true",
        help="create the agent workflow, competition brief, memory and first-round plan",
    )
    for command, help_text in (
        ("plan", "validate configuration and show pending commands without executing"),
        ("run", "execute pending experiments with explicit consent"),
        ("retry", "retry one failed or interrupted task"),
        ("status", "inspect the experiment ledger"),
        ("verify", "recheck all successful artifact hashes"),
        ("report", "print a Markdown experiment report"),
    ):
        sub = commands.add_parser(command, help=help_text)
        sub.add_argument("--root", type=Path, default=Path("."))
        if command in {"run", "retry"}:
            sub.add_argument(
                "--execute",
                action="store_true",
                help="confirm that you trust the configured local commands",
            )
        if command == "run":
            sub.add_argument("--steps", type=int)
        if command == "retry":
            sub.add_argument("task_id")
    check = commands.add_parser("check-submission", help="validate a prediction CSV")
    check.add_argument("path", type=Path)
    check.add_argument("--id-column", required=True)
    check.add_argument("--sample", type=Path)
    check.add_argument("--rows", type=int)
    check.add_argument("--allow-text", action="store_true")
    mix = commands.add_parser("blend", help="align and blend two prediction CSV files")
    mix.add_argument("anchor", type=Path)
    mix.add_argument("other", type=Path)
    mix.add_argument("--output", type=Path, required=True)
    mix.add_argument("--id-column", required=True)
    mix.add_argument("--weight", type=float, default=0.5)
    mix.add_argument("--method", choices=["mean", "rank"], default="mean")
    return p


def _report(root: Path):
    snapshot, checked = status(root), audit_evidence(root)
    config = load_config(root)
    print(f"# {config.name.replace(chr(10), ' ')}\n")
    print(f"Metric: `{config.metric}` ({config.direction}).")
    print(f"Evaluation: `{config.evaluation_id}`.")
    print(f"Artifact integrity: {'PASS' if checked['ok'] else 'FAIL'}.\n")
    print("| Task | Attempt | State | Decision | Score |")
    print("| --- | ---: | --- | --- | ---: |")
    for row in snapshot["history"]:
        score = "-" if row["score"] is None else f"{row['score']:.8g}"
        print(
            f"| {row['task_id']} | {row['attempt']} | {row['state']} "
            f"| {row['decision'] or '-'} | {score} |"
        )
    return 0 if checked["ok"] and snapshot["ok"] else 1


def dispatch(args):
    if args.command == "init":
        return initialize(args.path, competition=args.competition)
    if args.command == "check-submission":
        return check_submission(args.path, args.id_column, args.sample, args.rows, args.allow_text)
    if args.command == "blend":
        return blend(args.anchor, args.other, args.output, args.id_column, args.weight, args.method)
    root = args.root.resolve()
    if args.command == "plan":
        config = load_config(root)
        snapshot = status(root)
        attempted = {row["task_id"] for row in snapshot["history"]}
        return {
            "ok": True,
            "evaluation_id": config.evaluation_id,
            "config_sha256": config.fingerprint,
            "pending": [
                {"id": task.id, "hypothesis": task.hypothesis, "command": task.command}
                for task in config.tasks
                if task.id not in attempted
            ],
            "notice": "No commands executed. Review commands before using --execute.",
        }
    if args.command in {"run", "retry"}:
        if not args.execute:
            raise LoopError("commands are local code, not sandboxed; review plan and use --execute")
        return run(root, getattr(args, "steps", None), getattr(args, "task_id", None))
    if args.command == "status":
        return status(root)
    if args.command == "verify":
        return audit_evidence(root)
    raise LoopError("unknown command")


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "report":
            return _report(args.root.resolve())
        result = dispatch(args)
        print(json.dumps(result, indent=2, allow_nan=False))
        if result.get("stop_reason") == "interrupted":
            return 130
        return 0 if result["ok"] else 1
    except (LoopError, OSError, sqlite3.Error) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2
