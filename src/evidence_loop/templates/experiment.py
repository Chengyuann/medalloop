"""Small least-squares demonstration, not a competition benchmark."""

import argparse
import csv
import json
import os
import random
from pathlib import Path
from statistics import mean

parser = argparse.ArgumentParser()
parser.add_argument("--model", choices=["mean", "linear", "shifted"], required=True)
args = parser.parse_args()

rng = random.Random(42)
data = [(x := rng.uniform(-3, 3), 2.5 * x + 1.2 + rng.gauss(0, 0.3)) for _ in range(240)]
train, holdout = data[:160], data[160:]
mx, my = mean(x for x, _ in train), mean(y for _, y in train)
slope = sum((x - mx) * (y - my) for x, y in train) / sum((x - mx) ** 2 for x, _ in train)
predictions = [
    my if args.model == "mean" else my + slope * (x - mx) + (0.5 if args.model == "shifted" else 0)
    for x, _ in holdout
]
mse = mean((prediction - target) ** 2 for prediction, (_, target) in zip(predictions, holdout))
output = Path(os.environ["EVIDENCE_LOOP_RUN_DIR"])
(output / "metrics.json").write_text(
    json.dumps(
        {
            "metric": {"name": "mse", "value": mse},
            "evaluation_id": "synthetic-linear-v1-seed-42-holdout-80",
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
with (output / "predictions.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(["row_id", "prediction"])
    writer.writerows(enumerate(predictions))
print(json.dumps({"model": args.model, "holdout_rows": len(holdout), "mse": mse}))
