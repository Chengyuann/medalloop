# Round 001

This is a competition planning template, not a trained solution.

Before running:

1. Complete ../../COMPETITION.md and choose the actual metric, direction and evaluation ID.
2. Implement train.py and baseline.json for your competition.
3. Make train.py write metrics.json, oof.csv, submission.csv and config.json to
   MEDALLOOP_RUN_DIR. Adjust the declared artifacts for your task if necessary.
4. Add a small set of candidate tasks with one explicit hypothesis each.
5. Review the commands and compute limits before `medalloop run --execute`.

Keep the split and metric fixed within the round. After execution starts the
plan is immutable. Create a new round for a new plan, beginning with the previous
best as a freshly evaluated reference. Update the campaign memory after review.
