import csv

import pytest

from evidence_loop.config import LoopError
from evidence_loop.submission import blend, check_submission, ranks


def put(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "content",
    [
        "",
        "id,p\n",
        "id,p\n1,0.1,extra\n",
        "id,p\n1\n",
        "id,p,p\n1,1,2\n",
        "id,p\n1,0.1\n1,0.2\n",
        "id,p\n ,0.1\n",
        "id,p\n1,nan\n",
        "id,p\n1,inf\n",
        "id,p\n1,hello\n",
        "id,p\n1, \n",
        "id\n1\n",
        "id,\n1,2\n",
    ],
)
def test_invalid_csv(tmp_path, content):
    assert not check_submission(put(tmp_path, "input.csv", content), "id")["ok"]


def test_sample_order_and_text_labels(tmp_path):
    sample = put(tmp_path, "sample.csv", "id,p\n001,0\n002,0\n")
    labels = put(tmp_path, "labels.csv", "id,p\n001,yes\n002,no\n")
    assert check_submission(labels, "id", sample, allow_text=True)["ok"]
    swapped = put(tmp_path, "swapped.csv", "id,p\n002,0.1\n001,0.2\n")
    assert not check_submission(swapped, "id", sample)["ok"]


def test_semantically_constant_values_warn(tmp_path):
    result = check_submission(put(tmp_path, "x.csv", "id,p\n1,1\n2,1.0\n"), "id")
    assert result["ok"] and result["warnings"]


def test_tie_aware_rank():
    assert ranks([9, 9, 1, 5]) == [0.875, 0.875, 0.25, 0.5]
    assert ranks([]) == []
    assert ranks([2]) == [1]


def test_blend_aligns_ids_and_preserves_column_order(tmp_path):
    a = put(tmp_path, "a.csv", "p,id\n0.2,a\n0.8,b\n")
    b = put(tmp_path, "b.csv", "p,id\n0.6,b\n0.4,a\n")
    output = tmp_path / "blend.csv"
    assert blend(a, b, output, "id", 0.5)["ok"]
    with output.open() as handle:
        rows = list(csv.reader(handle))
    assert rows == [["p", "id"], ["0.3", "a"], ["0.7", "b"]]
    with pytest.raises(LoopError, match="already exists"):
        blend(a, b, output, "id", 0.5)


@pytest.mark.parametrize("weight", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_blend_weight(tmp_path, weight):
    with pytest.raises(LoopError):
        blend(tmp_path / "a", tmp_path / "b", tmp_path / "c", "id", weight)


def test_missing_id_never_silently_filled(tmp_path):
    a = put(tmp_path, "a.csv", "id,p\n1,0.1\n2,0.2\n")
    b = put(tmp_path, "b.csv", "id,p\n1,0.1\n3,0.2\n")
    with pytest.raises(LoopError, match="identical ID"):
        blend(a, b, tmp_path / "out.csv", "id", 0.5)
