"""Render a compact README image from the packaged offline demo ledger."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font(size: int, bold: bool = False):
    names = (
        "Arial Bold.ttf" if bold else "Arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    database = sqlite3.connect(args.database)
    database.row_factory = sqlite3.Row
    rows = database.execute(
        "SELECT task_id,state,decision,score FROM attempts ORDER BY sequence"
    ).fetchall()
    database.close()
    if not rows:
        raise SystemExit("ledger has no attempts")

    width, height = 1500, 600
    image = Image.new("RGB", (width, height), "#f5f6f3")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, 10), fill="#111827")
    draw.text((70, 50), "ONE OFFLINE RUN", font=font(22, True), fill="#dc5a3d")
    draw.text((70, 92), "Evidence decides what survives.", font=font(50, True), fill="#111827")
    draw.text(
        (70, 162),
        "Fixed synthetic holdout  |  metric: MSE (lower is better)",
        font=font(23),
        fill="#475569",
    )

    card_top, card_height = 245, 205
    gap = 20
    card_width = (width - 140 - gap * (len(rows) - 1)) // len(rows)
    for index, row in enumerate(rows):
        left = 70 + index * (card_width + gap)
        kept = row["decision"] == "keep"
        accent = "#078767" if kept else "#d65b3b"
        draw.rounded_rectangle(
            (left, card_top, left + card_width, card_top + card_height),
            radius=8,
            fill="#ffffff",
            outline="#d7dcd8",
            width=2,
        )
        draw.rectangle((left, card_top, left + 7, card_top + card_height), fill=accent)
        draw.text((left + 24, card_top + 24), f"{index + 1:02d}", font=font(18, True), fill=accent)
        draw.text((left + 24, card_top + 58), row["task_id"], font=font(24, True), fill="#111827")
        score = "-" if row["score"] is None else f"{row['score']:.5f}"
        draw.text((left + 24, card_top + 105), score, font=font(30, True), fill="#111827")
        draw.text(
            (left + 24, card_top + 155),
            (row["decision"] or row["state"]).upper(),
            font=font(17, True),
            fill=accent,
        )
    draw.text(
        (70, 510),
        "STOP  /  no improvement after two verified successful experiments",
        font=font(22, True),
        fill="#111827",
    )
    draw.text(
        (70, 552),
        "Rendered from ledger.sqlite3; toy values are not benchmark claims.",
        font=font(18),
        fill="#64748b",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, optimize=True)


if __name__ == "__main__":
    main()
