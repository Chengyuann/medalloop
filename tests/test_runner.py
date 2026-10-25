import json
import os
import subprocess
import sys

import pytest

from medalloop.config import LoopError, load_config
from medalloop.runner import audit_evidence, run, status
from medalloop.store import Store, workspace_lock


def task(
    task_id="trial", score=1.0, evaluation="test-v1", metric="score", extra="", artifacts=None
):
    code = (
        "import os,json;from pathlib import Path;"
        "p=Path(os.environ['MEDALLOOP_RUN_DIR']);"
        f"(p/'metrics.json').write_text(json.dumps({{'metric':{{'name':{metric!r},"
        f"'value':{score!r}}},'evaluation_id':{evaluation!r}}}));{extra}"
    )
    return {
        "id": task_id,
        "hypothesis": "Measure the controlled fixture.",
        "command": ["{python}", "-c", code],
        "artifacts": artifacts or [],
    }


def test_complete_demo_and_resume(workspace):
    result = run(workspace)
    assert result["ok"]
    assert result["stop_reason"] == "no_improvement"
    assert result["executed"] == 4
    assert result["best"]["task_id"] == "linear"
    assert [r["decision"] for r in result["history"]] == ["keep", "keep", "reject", "reject"]
    assert result["history"][1]["score"] == result["history"][3]["score"]
    assert audit_evidence(workspace)["ok"]
    assert run(workspace)["executed"] == 0
    assert run(workspace)["stop_reason"] == "no_improvement"


def test_stepwise_resume(workspace):
    assert run(workspace, 1)["executed"] == 1
    second = run(workspace, 1)
    assert second["attempts"] == 2
    assert second["best"]["task_id"] == "linear"
    assert second["history"][0]["attempt"] == 1


@pytest.mark.parametrize("direction,expected", [("maximize", "high"), ("minimize", "low")])
def test_metric_direction(workspace, configure, direction, expected):
    configure(
        metric={"name": "score", "direction": direction},
        evaluation_id="test-v1",
        tasks=[task("low", 1), task("high", 2)],
    )
    result = run(workspace)
    assert result["ok"], result
    assert result["best"]["task_id"] == expected


@pytest.mark.parametrize(
    "bad",
    [
        task(score="not-a-number"),
        task(evaluation="wrong"),
        task(metric="wrong"),
        task(artifacts=["missing.csv"]),
        task(extra='(p/\'metrics.json\').write_text(\'{"metric":{"name":"score","value":NaN}}\')'),
        task(extra="raise RuntimeError('fixture failure')"),
    ],
)
def test_failed_verification(workspace, configure, bad):
    configure(
        metric={"name": "score", "direction": "maximize"}, evaluation_id="test-v1", tasks=[bad]
    )
    result = run(workspace)
    assert not result["ok"]
    assert result["best"] is None
    assert result["history"][0]["state"] == "failed"
    assert run(workspace)["executed"] == 0
    assert not audit_evidence(workspace)["ok"]


def test_timeout_and_failure_circuit(workspace, configure):
    slow = task()
    slow["command"] = ["{python}", "-c", "import time;time.sleep(20)"]
    configure(tasks=[slow, task("pending")], budget={"timeout": 0.05, "max_failures": 1})
    result = run(workspace)
    assert not result["ok"]
    assert result["executed"] == 1
    assert result["stop_reason"] == "consecutive_failures"
    assert "timed out" in result["history"][0]["reason"]
    assert result["history"][0]["duration"] < 10


def test_retry_requires_explicit_request_and_retains_failure(workspace, configure):
    conditional = task(extra="assert Path('ready').exists()")
    configure(
        metric={"name": "score", "direction": "maximize"},
        evaluation_id="test-v1",
        tasks=[conditional],
        budget={"max_failures": 1},
    )
    assert not run(workspace)["ok"]
    assert run(workspace)["executed"] == 0
    (workspace / "ready").touch()
    result = run(workspace, retry_task="trial")
    assert result["ok"], result
    assert result["attempts"] == 2
    assert result["history"][0]["state"] == "failed"
    assert result["history"][1]["attempt"] == 2
    with pytest.raises(LoopError):
        run(workspace, retry_task="trial")


def test_recovery_never_repeats_orphan(workspace):
    store = Store(workspace)
    store.bind(load_config(workspace).fingerprint)
    store.start("baseline")
    store.close()
    assert not status(workspace)["ok"]
    result = run(workspace, 1)
    assert result["history"][0]["state"] == "interrupted"
    assert result["history"][1]["task_id"] == "linear"


def test_config_change_refused(workspace, configure):
    run(workspace, 1)
    configure(evaluation_id="changed")
    with pytest.raises(LoopError, match="configuration changed"):
        run(workspace)


def test_tampering_detected_before_continuing(workspace):
    run(workspace, 1)
    (workspace / "runs/baseline/attempt-001/predictions.csv").write_text("changed")
    assert not audit_evidence(workspace)["ok"]
    with pytest.raises(LoopError, match="existing evidence changed"):
        run(workspace)


def test_total_attempt_budget(workspace, configure):
    configure(budget={"max_steps": 1})
    assert run(workspace)["stop_reason"] == "max_steps"
    assert run(workspace)["executed"] == 0


def test_total_wall_budget(workspace, configure):
    configure(budget={"max_wall_seconds": 0.01})
    result = run(workspace)
    assert result["stop_reason"] == "wall_time_budget"
    assert result["attempts"] == 1


def test_workspace_lock_is_exclusive(workspace):
    with workspace_lock(workspace):
        result = subprocess.run(
            [sys.executable, "-m", "medalloop", "run", "--root", str(workspace), "--execute"],
            capture_output=True,
            text=True,
        )
    assert result.returncode == 2
    assert "another runner" in result.stderr


def test_retry_does_not_bypass_attempt_budget(workspace, configure):
    configure(tasks=[task(extra="raise ValueError()")], budget={"max_steps": 1})
    run(workspace)
    result = run(workspace, retry_task="trial")
    assert result["executed"] == 0
    assert result["stop_reason"] == "max_steps"


@pytest.mark.skipif(os.name != "posix", reason="POSIX process groups")
def test_timeout_terminates_descendants(workspace, configure):
    code = (
        "import subprocess,sys,time,os;from pathlib import Path;"
        "p=Path(os.environ['MEDALLOOP_RUN_DIR']);"
        "subprocess.Popen([sys.executable,'-c',"
        "\"import time;from pathlib import Path;time.sleep(1);Path('leaked').touch()\"]);"
        "time.sleep(10)"
    )
    job = task()
    job["command"] = ["{python}", "-c", code]
    configure(tasks=[job], budget={"timeout": 0.2})
    assert not run(workspace)["ok"]
    import time

    time.sleep(1.2)
    assert not (workspace / "leaked").exists()


def test_provenance_contains_code_hash_not_environment(workspace):
    run(workspace, 1)
    payload = json.loads((workspace / "runs/baseline/attempt-001/provenance.json").read_text())
    assert payload["input_files"][0]["path"] == "experiment.py"
    assert len(payload["input_files"][0]["sha256"]) == 64
    assert "environment" not in payload


def test_nonfile_argv_does_not_fail_optional_provenance(workspace, configure, monkeypatch):
    from medalloop import runner

    original = runner.contained

    def reject_inline_path(root, relative):
        if relative.startswith("import os,json;"):
            raise OSError("Invalid filename on this platform")
        return original(root, relative)

    configure(
        metric={"name": "score", "direction": "maximize"},
        evaluation_id="test-v1",
        tasks=[task()],
    )
    monkeypatch.setattr(runner, "contained", reject_inline_path)
    assert run(workspace)["ok"]


def test_legacy_output_environment_is_preserved(workspace, configure):
    job = task(
        extra=(
            "assert os.environ['EVIDENCE_LOOP_RUN_DIR']==os.environ['MEDALLOOP_RUN_DIR'];"
            "assert os.environ['EVIDENCE_LOOP_TASK_ID']==os.environ['MEDALLOOP_TASK_ID']"
        )
    )
    job["command"][-1] = job["command"][-1].replace(
        "p=Path(os.environ['MEDALLOOP_RUN_DIR'])",
        "p=Path(os.environ['EVIDENCE_LOOP_RUN_DIR'])",
    )
    configure(
        metric={"name": "score", "direction": "maximize"},
        evaluation_id="test-v1",
        tasks=[job],
    )
    assert run(workspace)["ok"]
    assert (workspace / ".evidence-loop.lock").is_file()
