import json

import pytest

from medalloop.cli import initialize


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "workspace"
    initialize(root)
    return root


@pytest.fixture
def configure(workspace):
    def update(**changes):
        path = workspace / "loop.json"
        data = json.loads(path.read_text())
        data.update(changes)
        path.write_text(json.dumps(data), encoding="utf-8")
        return data

    return update
