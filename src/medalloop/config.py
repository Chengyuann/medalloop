from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


class LoopError(ValueError):
    """An actionable configuration, validation, or workflow error."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LoopError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                LoopError(f"non-finite JSON number: {value}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LoopError(f"cannot read {path.name}: {exc}") from exc


def number(value: Any, name: str, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LoopError(f"{name} must be a finite number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise LoopError(f"{name} must be a finite number")
    if minimum is not None and value < minimum:
        raise LoopError(f"{name} must be >= {minimum}")
    return float(value)


def relative_path(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise LoopError(f"{name} must be a nonempty portable relative path")
    posix, windows = PurePosixPath(value), PureWindowsPath(value)
    if posix.is_absolute() or windows.drive or ".." in posix.parts or not posix.parts:
        raise LoopError(f"{name} must stay inside its directory")
    return posix.as_posix()


def contained(root: Path, relative: str) -> Path:
    path = root / relative_path(relative, "artifact path")
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise LoopError("artifact path escapes its directory") from exc
    return path


def _object(value: Any, allowed: set[str], name: str) -> dict:
    if not isinstance(value, dict):
        raise LoopError(f"{name} must be an object")
    unknown = set(value) - allowed
    if unknown:
        raise LoopError(f"unknown {name} fields: {', '.join(sorted(unknown))}")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LoopError(f"{name} must be a nonempty string")
    return value


@dataclass(frozen=True)
class Task:
    id: str
    hypothesis: str
    command: tuple[str, ...]
    metrics: str
    artifacts: tuple[str, ...]


@dataclass(frozen=True)
class Config:
    name: str
    metric: str
    direction: str
    evaluation_id: str
    max_steps: int
    max_failures: int
    patience: int
    min_delta: float
    timeout: float
    max_wall_seconds: float
    tasks: tuple[Task, ...]
    fingerprint: str


def load_config(root: Path) -> Config:
    raw = _object(
        read_json(root / "loop.json"),
        {"name", "metric", "evaluation_id", "budget", "tasks"},
        "config",
    )
    metric = _object(raw.get("metric"), {"name", "direction"}, "metric")
    direction = metric.get("direction")
    if direction not in {"maximize", "minimize"}:
        raise LoopError("metric.direction must be maximize or minimize")
    budget = _object(
        raw.get("budget", {}),
        {"max_steps", "max_failures", "patience", "min_delta", "timeout", "max_wall_seconds"},
        "budget",
    )
    counts = {}
    for key, default in (("max_steps", 10), ("max_failures", 2), ("patience", 3)):
        value = budget.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise LoopError(f"budget.{key} must be a positive integer")
        counts[key] = value
    tasks = raw.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise LoopError("tasks must be a nonempty list")
    parsed, ids = [], set()
    for item in tasks:
        task = _object(item, {"id", "hypothesis", "command", "metrics", "artifacts"}, "task")
        task_id = _text(task.get("id"), "task.id")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", task_id) or task_id in ids:
            raise LoopError("task IDs must be unique, portable names of 1-64 characters")
        ids.add(task_id)
        command = task.get("command")
        if (
            not isinstance(command, list)
            or not command
            or any(not isinstance(arg, str) or "\x00" in arg for arg in command)
            or not command[0]
        ):
            raise LoopError(f"{task_id}: command must be a nonempty argv list")
        artifacts = task.get("artifacts", [])
        if not isinstance(artifacts, list):
            raise LoopError(f"{task_id}: artifacts must be a list")
        paths = tuple(relative_path(p, "artifact") for p in artifacts)
        metrics_path = relative_path(task.get("metrics", "metrics.json"), "metrics")
        outputs = [metrics_path, *paths]
        if len(set(outputs)) != len(outputs):
            raise LoopError(f"{task_id}: output paths must be distinct")
        if any(
            PurePosixPath(p).parts[0] in {"stdout.log", "stderr.log", "provenance.json"}
            for p in outputs
        ):
            raise LoopError(f"{task_id}: output path collides with reserved logs")
        parsed.append(
            Task(
                task_id,
                _text(task.get("hypothesis"), "hypothesis"),
                tuple(command),
                metrics_path,
                paths,
            )
        )
    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return Config(
        name=_text(raw.get("name"), "name"),
        metric=_text(metric.get("name"), "metric.name"),
        direction=direction,
        evaluation_id=_text(raw.get("evaluation_id"), "evaluation_id"),
        **counts,
        min_delta=number(budget.get("min_delta", 0), "min_delta", 0),
        timeout=number(budget.get("timeout", 300), "timeout", 0.01),
        max_wall_seconds=number(budget.get("max_wall_seconds", 3600), "max_wall_seconds", 0.01),
        tasks=tuple(parsed),
        fingerprint=hashlib.sha256(canonical).hexdigest(),
    )
