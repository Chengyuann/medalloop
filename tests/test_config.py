import json
import math

import pytest

from evidence_loop.config import LoopError, contained, load_config, number, read_json, relative_path


def test_demo_valid(workspace):
    config = load_config(workspace)
    assert config.direction == "minimize"
    assert len(config.tasks) == 5
    assert len(config.fingerprint) == 64


@pytest.mark.parametrize(
    "value",
    [
        "../escape",
        "/tmp/escape",
        "C:/escape",
        "\\\\host\\file",
        "foo/../../escape",
        "",
        ".",
        "a\x00b",
        1,
    ],
)
def test_path_rejected(value):
    with pytest.raises(LoopError):
        relative_path(value, "test")


@pytest.mark.parametrize("value", [True, "0.5", None, math.nan, math.inf, -math.inf, 10**400])
def test_nonfinite_and_nonnumeric(value):
    with pytest.raises(LoopError):
        number(value, "test")


@pytest.mark.parametrize("raw", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', "{"])
def test_strict_json(tmp_path, raw):
    path = tmp_path / "data.json"
    path.write_text(raw)
    with pytest.raises(LoopError):
        read_json(path)


@pytest.mark.parametrize(
    "changes",
    [
        {"typo": True},
        {"metric": {"name": "mse", "direction": "up"}},
        {"budget": {"max_steps": 0}},
        {"budget": {"max_steps": True}},
        {"budget": {"patience": -1}},
        {"budget": {"timeout": 0}},
        {"budget": {"unknown": 1}},
        {"tasks": []},
        {"evaluation_id": ""},
    ],
)
def test_bad_config(workspace, configure, changes):
    configure(**changes)
    with pytest.raises(LoopError):
        load_config(workspace)


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "../../outside"),
        ("command", "python experiment.py"),
        ("command", []),
        ("command", [""]),
        ("command", ["a\x00b"]),
        ("artifacts", ["stdout.log"]),
        ("artifacts", ["metrics.json"]),
        ("artifacts", ["../secret"]),
        ("hypothesis", ""),
    ],
)
def test_bad_task(workspace, configure, field, value):
    data = json.loads((workspace / "loop.json").read_text())
    data["tasks"][0][field] = value
    configure(tasks=data["tasks"])
    with pytest.raises(LoopError):
        load_config(workspace)


def test_symlink_escape(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("private")
    try:
        (root / "escape").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable on this host")
    with pytest.raises(LoopError):
        contained(root, "escape")


def test_config_hash_ignores_key_order(workspace):
    first = load_config(workspace).fingerprint
    path = workspace / "loop.json"
    path.write_text(json.dumps(json.loads(path.read_text()), sort_keys=True, indent=3))
    assert load_config(workspace).fingerprint == first


@pytest.mark.parametrize("path", ["./", "././"])
def test_directory_alias_rejected(path):
    with pytest.raises(LoopError):
        relative_path(path, "artifact")


def test_output_alias_collision(workspace, configure):
    data = json.loads((workspace / "loop.json").read_text())
    data["tasks"][0]["artifacts"] = ["./metrics.json"]
    configure(tasks=data["tasks"])
    with pytest.raises(LoopError, match="distinct"):
        load_config(workspace)
