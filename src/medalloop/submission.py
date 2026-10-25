from __future__ import annotations

import csv
import math
import os
import tempfile
from pathlib import Path

from .config import LoopError, number


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            header = next(reader, [])
            if not header or any(not col.strip() for col in header):
                raise LoopError("CSV must have nonempty column names")
            if len(set(header)) != len(header):
                raise LoopError("CSV has duplicate column names")
            rows = []
            for line, row in enumerate(reader, 2):
                if len(row) != len(header):
                    raise LoopError(f"CSV row {line} has {len(row)} cells; expected {len(header)}")
                rows.append(row)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise LoopError(f"cannot read CSV: {exc}") from exc
    if not rows:
        raise LoopError("CSV has no data rows")
    return header, rows


def _ids(header: list[str], rows: list[list[str]], id_col: str) -> list[str]:
    if id_col not in header:
        raise LoopError(f"missing ID column: {id_col}")
    ids = [row[header.index(id_col)] for row in rows]
    if any(not value.strip() for value in ids):
        raise LoopError("CSV has blank IDs")
    if len(ids) != len(set(ids)):
        raise LoopError("CSV has duplicate IDs")
    return ids


def _predictions(header, rows, id_col, allow_text=False):
    columns = [col for col in header if col != id_col]
    if not columns:
        raise LoopError("CSV has no prediction columns")
    warnings, values = [], {}
    for col in columns:
        raw = [row[header.index(col)] for row in rows]
        parsed = []
        for value in raw:
            if not value.strip():
                raise LoopError(f"blank prediction in {col}")
            try:
                numeric = float(value)
            except ValueError:
                if not allow_text:
                    raise LoopError(f"nonnumeric prediction in {col}") from None
                parsed.append(value)
            else:
                if not math.isfinite(numeric):
                    raise LoopError(f"non-finite prediction in {col}")
                parsed.append(numeric)
        if len(set(parsed)) == 1:
            warnings.append(f"constant predictions in {col}")
        values[col] = parsed
    return values, warnings


def check_submission(
    path: Path,
    id_col: str,
    sample: Path | None = None,
    expected_rows: int | None = None,
    allow_text=False,
) -> dict:
    try:
        header, rows = read_csv(path)
        ids = _ids(header, rows, id_col)
        _, warnings = _predictions(header, rows, id_col, allow_text)
        if expected_rows is not None and len(rows) != expected_rows:
            raise LoopError("row count does not match expected_rows")
        if sample is not None:
            sample_header, sample_rows = read_csv(sample)
            sample_ids = _ids(sample_header, sample_rows, id_col)
            if header != sample_header:
                raise LoopError("column names or order differ from the sample")
            if ids != sample_ids:
                raise LoopError("IDs or row order differ from the sample")
        return {
            "ok": True,
            "rows": len(rows),
            "columns": header,
            "warnings": warnings,
            "errors": [],
        }
    except LoopError as exc:
        return {"ok": False, "errors": [str(exc)], "warnings": []}


def ranks(values: list[float]) -> list[float]:
    """Average ranks for ties, normalized to (0, 1]."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    result, start = [0.0] * len(values), 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        average = (start + 1 + end) / (2 * len(order))
        for index in order[start:end]:
            result[index] = average
        start = end
    return result


def blend(
    anchor: Path, other: Path, output: Path, id_col: str, weight: float, method: str = "mean"
) -> dict:
    number(weight, "weight", 0)
    if weight > 1:
        raise LoopError("weight must be <= 1")
    if method not in {"mean", "rank"}:
        raise LoopError("method must be mean or rank")
    if output.exists():
        raise LoopError("output already exists; choose a new path")
    ah, ar = read_csv(anchor)
    bh, br = read_csv(other)
    ai, bi = _ids(ah, ar, id_col), _ids(bh, br, id_col)
    if set(ai) != set(bi) or ah != bh:
        raise LoopError("blend inputs must have identical ID sets and ordered columns")
    av, _ = _predictions(ah, ar, id_col)
    bv, _ = _predictions(bh, br, id_col)
    lookup = {value: index for index, value in enumerate(bi)}
    predictions = {}
    for col in av:
        left, right = av[col], [bv[col][lookup[value]] for value in ai]
        if method == "rank":
            left, right = ranks(left), ranks(right)
        mixed = [(1 - weight) * a + weight * b for a, b in zip(left, right)]
        if any(not math.isfinite(value) for value in mixed):
            raise LoopError("blend produced non-finite values")
        predictions[col] = mixed
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=output.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            writer = csv.writer(handle)
            writer.writerow(ah)
            for index, value in enumerate(ai):
                writer.writerow(
                    [value if col == id_col else f"{predictions[col][index]:.12g}" for col in ah]
                )
        result = check_submission(temporary, id_col)
        if not result["ok"]:
            raise LoopError("; ".join(result["errors"]))
        # A hard link atomically refuses an output created by another process.
        os.link(temporary, output)
        return result
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
