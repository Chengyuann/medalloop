from __future__ import annotations

import hashlib
import json
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path

from .config import Config, LoopError, contained, load_config, number, read_json
from .store import Store, workspace_lock


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def best(rows: list[dict]) -> dict | None:
    return next(
        (
            row
            for row in reversed(rows)
            if row["state"] == "succeeded" and row["decision"] == "keep"
        ),
        None,
    )


def _stop_reason(rows: list[dict], config: Config, ignore_circuit=False) -> str | None:
    if len(rows) >= config.max_steps:
        return "max_steps"
    if sum(row["duration"] for row in rows) >= config.max_wall_seconds:
        return "wall_time_budget"
    if ignore_circuit:
        return None
    failures = 0
    for row in reversed(rows):
        if row["state"] not in {"failed", "interrupted"}:
            break
        failures += 1
    if failures >= config.max_failures:
        return "consecutive_failures"
    champion = best(rows)
    if champion:
        no_gain = sum(
            row["state"] == "succeeded" and row["sequence"] > champion["sequence"] for row in rows
        )
        if no_gain >= config.patience:
            return "no_improvement"
    return None


def _terminate(process):
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        if os.name != "posix":
            process.kill()
    finally:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait()


def execute(command: tuple[str, ...], root: Path, run_dir: Path, task_id: str, timeout: float):
    argv = [sys.executable if arg == "{python}" else arg for arg in command]
    env = dict(
        os.environ,
        MEDALLOOP_RUN_DIR=str(run_dir),
        MEDALLOOP_TASK_ID=task_id,
        EVIDENCE_LOOP_RUN_DIR=str(run_dir),
        EVIDENCE_LOOP_TASK_ID=task_id,
    )
    with (run_dir / "stdout.log").open("wb") as out, (run_dir / "stderr.log").open("wb") as err:
        process = subprocess.Popen(
            argv,
            cwd=root,
            env=env,
            stdout=out,
            stderr=err,
            shell=False,
            start_new_session=(os.name == "posix"),
        )
        try:
            code = process.wait(timeout=timeout)
            if code != 0:
                raise LoopError(f"command exited with code {code}; inspect local stderr.log")
        except subprocess.TimeoutExpired as exc:
            raise LoopError(f"command timed out after {timeout:.2f}s") from exc
        finally:
            _terminate(process)


def verify_outputs(config: Config, task, run_dir: Path, root: Path) -> tuple[float, list[dict]]:
    metrics_file = contained(run_dir, task.metrics)
    if not metrics_file.is_file():
        raise LoopError("metrics must be a readable regular file")
    payload = read_json(metrics_file)
    if not isinstance(payload, dict) or not isinstance(payload.get("metric"), dict):
        raise LoopError("metrics must contain a metric object")
    if payload.get("evaluation_id") != config.evaluation_id:
        raise LoopError("evaluation_id does not match the frozen evaluation protocol")
    if payload["metric"].get("name") != config.metric:
        raise LoopError("metric name does not match the configured metric")
    score = number(payload["metric"].get("value"), "metric.value")
    evidence = []
    for relative in (task.metrics, *task.artifacts, "stdout.log", "stderr.log", "provenance.json"):
        path = contained(run_dir, relative)
        if not path.is_file():
            raise LoopError(f"required artifact missing: {relative}")
        evidence.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": digest(path),
                "bytes": path.stat().st_size,
            }
        )
    return score, evidence


def run(root: Path, step_limit: int | None = None, retry_task: str | None = None) -> dict:
    root = root.resolve()
    config = load_config(root)
    if step_limit is not None and (isinstance(step_limit, bool) or step_limit < 1):
        raise LoopError("steps must be positive")
    with workspace_lock(root):
        store = Store(root)
        try:
            store.bind(config.fingerprint)
            store.recover()
            rows = store.rows()
            if any(row["state"] == "succeeded" for row in rows):
                checked = audit_evidence(root)
                if not checked["ok"]:
                    raise LoopError("existing evidence changed; inspect verify before continuing")
            previous = {row["task_id"]: row for row in rows}
            if retry_task is not None:
                prior = previous.get(retry_task)
                if not prior or prior["state"] not in {"failed", "interrupted"}:
                    raise LoopError("retry requires a failed or interrupted task")
                tasks = [task for task in config.tasks if task.id == retry_task]
            else:
                tasks = [task for task in config.tasks if task.id not in previous]
            executed, stop = 0, "completed"
            for task in tasks:
                rows = store.rows()
                stop = _stop_reason(rows, config, ignore_circuit=retry_task is not None)
                if stop:
                    break
                if step_limit is not None and executed >= step_limit:
                    stop = "step_limit"
                    break
                attempt = store.start(task.id)
                run_dir = contained(root, f"runs/{task.id}/attempt-{attempt['attempt']:03d}")
                started = time.monotonic()
                state, decision, score, evidence = "failed", "reject", None, []
                reason, interrupted = "", False
                try:
                    run_dir.mkdir(parents=True, exist_ok=False)
                    inputs = []
                    for arg in task.command:
                        try:
                            path = contained(root, arg)
                            if path.is_file():
                                inputs.append({"path": arg, "sha256": digest(path)})
                        except (LoopError, OSError, ValueError):
                            # An argv item may be inline code, not a valid host filesystem path.
                            continue
                    (run_dir / "provenance.json").write_text(
                        json.dumps(
                            {
                                "config_sha256": config.fingerprint,
                                "command": task.command,
                                "python_version": platform.python_version(),
                                "input_files": inputs,
                            },
                            indent=2,
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                    remaining = config.max_wall_seconds - sum(row["duration"] for row in rows)
                    execute(task.command, root, run_dir, task.id, min(config.timeout, remaining))
                    score, evidence = verify_outputs(config, task, run_dir, root)
                    champion = best(rows)
                    delta = None if champion is None else score - champion["score"]
                    if delta is not None and config.direction == "minimize":
                        delta = -delta
                    decision = "keep" if delta is None or delta > config.min_delta else "reject"
                    state = "succeeded"
                    reason = (
                        "First verified result."
                        if delta is None
                        else (f"Directional delta {delta:.8g}; must exceed {config.min_delta:.8g}.")
                    )
                except KeyboardInterrupt:
                    state, reason, interrupted = "interrupted", "Interrupted by the operator.", True
                except (LoopError, OSError) as exc:
                    reason = str(exc)
                store.finish(
                    attempt["sequence"],
                    state,
                    decision,
                    score,
                    time.monotonic() - started,
                    reason,
                    evidence,
                )
                executed += 1
                if interrupted:
                    return _summary(store.rows(), "interrupted", executed)
                stop = "completed"
            return _summary(store.rows(), stop, executed)
        finally:
            store.close()


def _summary(rows: list[dict], reason: str, executed: int = 0) -> dict:
    failed = any(
        row["state"] in {"failed", "interrupted", "running"}
        for row in {row["task_id"]: row for row in rows}.values()
    )
    return {
        "ok": not failed,
        "stop_reason": reason,
        "executed": executed,
        "attempts": len(rows),
        "best": best(rows),
        "history": rows,
    }


def status(root: Path) -> dict:
    config = load_config(root)
    if not (root / "ledger.sqlite3").exists():
        return _summary([], "not_started")
    store = Store(root)
    try:
        store.bind(config.fingerprint)
        return _summary(store.rows(), "snapshot")
    finally:
        store.close()


def audit_evidence(root: Path) -> dict:
    snapshot = status(root)
    errors = []
    if not any(row["state"] == "succeeded" for row in snapshot["history"]):
        errors.append("no verified experiment evidence yet")
    for row in snapshot["history"]:
        if row["state"] != "succeeded":
            continue
        if not row["evidence"]:
            errors.append(f"{row['task_id']}: missing evidence manifest")
        for artifact in row["evidence"]:
            try:
                path = contained(root, artifact["path"])
                if path.stat().st_size != artifact["bytes"] or digest(path) != artifact["sha256"]:
                    errors.append(f"artifact changed: {artifact['path']}")
            except (OSError, LoopError):
                errors.append(f"artifact unavailable: {artifact['path']}")
    return {"ok": not errors, "errors": errors}
