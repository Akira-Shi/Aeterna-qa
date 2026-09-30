# build-readme

Files: new README.md (repo root); Documents/README.md (one-line outdated pointer added at top); Documents/Documentation.md (changelog entry).

Checked against code/docs: CLI flags (pipeline --help, explain --help), all four module tests and frozen_check run and pass (exit 0), ops menu and MAX_ITERATIONS=16 from config.py, MIN_STAGE_GAIN_FRAC 0.25, commit rule (delta>0 and >= t-crit*SE, Bonferroni over MAX_ITERATIONS), 5x3 folds, RESULTS.md counts and per-scenario k/n, D1 is demo, .env location (repo root, per config.py). No retracted numbers cited.

Uncertain: "python -m modules.pipeline" with no flags = real Adult (from code reading, not run). Python 3.10+ taken from CLAUDE.md. "Noise" rollback described as positive-but-below-bar (per explain.py), not literally "half the bar". Nothing run against Groq.
