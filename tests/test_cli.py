import json

import pytest

from medalloop.cli import initialize, main
from medalloop.config import LoopError


def test_no_execution_without_consent(workspace, capsys):
    assert main(["run", "--root", str(workspace)]) == 2
    assert not (workspace / "ledger.sqlite3").exists()
    assert "not sandboxed" in capsys.readouterr().err


def test_plan_is_machine_readable_and_does_not_create_ledger(workspace, capsys):
    assert main(["plan", "--root", str(workspace)]) == 0
    assert len(json.loads(capsys.readouterr().out)["pending"]) == 5
    assert not (workspace / "ledger.sqlite3").exists()


def test_existing_directory_not_overwritten(workspace):
    with pytest.raises(LoopError):
        initialize(workspace)
    assert (workspace / "experiment.py").exists()


def test_cli_demo_report(workspace, capsys):
    assert main(["run", "--root", str(workspace), "--execute"]) == 0
    capsys.readouterr()
    assert main(["report", "--root", str(workspace)]) == 0
    report = capsys.readouterr().out
    assert "PASS" in report
    assert "| linear | 1 | succeeded | keep |" in report


def test_no_evidence_is_not_pass(workspace):
    assert main(["verify", "--root", str(workspace)]) == 1


def test_competition_scaffold(tmp_path, capsys):
    root = tmp_path / "competition"
    assert main(["init", str(root), "--competition"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["mode"] == "competition"
    assert (root / "COMPETITION.md").is_file()
    assert (root / "memory/STATE.md").is_file()
    assert (root / "memory/HYPOTHESES.md").is_file()
    assert (root / "memory/RESULTS.md").is_file()
    assert (root / "rounds/001/loop.json").is_file()
    assert not (root / "rounds/001/train.py").exists()
    assert "not a trained solution" in (root / "rounds/001/README.md").read_text()
    assert "## 6. Ensemble and Submit" in (root / "AGENTS.md").read_text()
    assert "MEDALLOOP_RUN_DIR" in (root / "AGENTS.md").read_text()
    assert main(["plan", "--root", str(root / "rounds/001")]) == 0
    assert not (root / "rounds/001/ledger.sqlite3").exists()


def test_competition_init_preserves_existing_directory(workspace):
    with pytest.raises(LoopError):
        initialize(workspace, competition=True)
    assert (workspace / "experiment.py").is_file()
