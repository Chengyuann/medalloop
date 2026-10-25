import json

import pytest

from evidence_loop.cli import initialize, main
from evidence_loop.config import LoopError


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
