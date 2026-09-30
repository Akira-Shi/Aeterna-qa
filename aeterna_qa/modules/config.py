"""
AETERNA-QA configuration.

Loads GROQ_API_KEY from a .env file at the Capstone repo root (one level up
from aeterna_qa/). Never hardcode the key here, never commit .env.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Repo root is one level above aeterna_qa/
REPO_ROOT = Path(__file__).resolve().parents[2]
AETERNA_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(REPO_ROOT / ".env")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MODEL_NAME = "openai/gpt-oss-20b"  # llama-3.3-70b-versatile moved to Groq Enterprise tier, confirmed unavailable to free key 2026-09-29

DATA_PATH = AETERNA_ROOT / "data" / "adult.csv"
LOG_DIR = AETERNA_ROOT / "logs"

TARGET_COLUMN = "income"
POSITIVE_CLASS = ">50K"  # after stripping whitespace

RANDOM_STATE = 42

# Evaluator model used for every accept/commit decision (2026-09-30). Declared INPUT, not
# tuned per run. "rf" = RandomForest (original; insensitive to sentinels/spelling variants).
# "lr" = StandardScaler + LogisticRegression, scaler fitted on each fold's TRAINING rows only.
# Both are reported; the guide accepted this. Choose on the CLI with --evaluator.
EVALUATOR = "lr"   # 2026-09-30: LR is the study evaluator (RF is blind to the injected defects); "rf" kept only to reproduce old numbers
EVALUATORS = ("rf", "lr")

# Gate metric (2026-09-30, signed off by Akira): "brier" = negative Brier score of the predicted
# probabilities, so a HIGHER score is better and a positive paired delta means improvement.
# F1 is always computed and reported next to every decision but is not the gate. "f1" restores
# the old gate.
GATE_METRIC = "brier"
METRIC_LABEL = {"brier": "neg-Brier", "f1": "F1"}[GATE_METRIC]
TEST_SIZE = 0.2
CV_FOLDS = 5
CV_REPEATS = 3  # (2026-09-29) repeated CV -- folds are fixed once per run from the raw
# dataset (evaluator.make_fixed_folds) and reused for every comparison, so this gives
# CV_FOLDS * CV_REPEATS = 15 paired fold-level comparisons per accept/commit decision.

# Fixed operation menu — the planner can only choose from these, never
# generate freeform code. This is a deliberate safety/reliability choice,
# not a shortcut (see Documentation.md decisions, 2026-09-04 / carried
# forward).
OPERATION_MENU = [
    "fill_mean",
    "fill_median",
    "fill_mode",
    "drop_rows",
    "clip_outliers",
    "fill_unknown",  # added 2026-09-29 -- explicit missing-as-its-own-category baseline
    # added 2026-09-30 (detector-driven planning). Each is fitted on TRAINING rows only:
    "normalize_categories",  # merge case/space/punctuation spellings into the dominant one
    "sentinel_to_median",    # replace a missing-value code (999, 99999...) with the train median
    "rescale_units",         # divide an upper cluster (e.g. months in a years column) by a fitted factor from {12,100,1000}
    "dedupe_rows",           # drop exact duplicate rows from TRAINING only (column key "*")
]

# Replaces the old fixed F1_DELTA_THRESHOLD=0.005 guess (2026-09-29,
# CV-hardening). That fixed number had no justification beyond "it drew
# the right line once" -- and it turned out to be wrong: under the old
# single train/test split, native.country/drop_rows measured +0.0067 and
# was accepted, but under 5-fold CV the same operation measures -0.0006
# (noise, not a real improvement). Fixed thresholds compared against a
# single noisy split can't tell a real gain from a lucky split.
#
# Instead: every accept/rollback decision now computes its own threshold
# from the CURRENT baseline's measured fold-to-fold standard error
# (std / sqrt(CV_FOLDS)), scaled by this multiplier. A delta must clear
# THRESHOLD_SE_MULTIPLIER standard errors above the measurement noise to
# be accepted. 2.0 is an approximate ~95%-ish one-sided bar assuming
# roughly normal fold-to-fold variation -- CV folds share overlapping
# training data so they aren't fully independent samples, which means
# this is a reasonable heuristic bar, not a rigorous p-value. Revisit if
# accept/reject calls still look shaky in practice.
# 2026-09-29, third revision (Bonferroni correction): a review found that
# staging up to MAX_ITERATIONS proposals against one baseline in a single
# run, each checked at a ~2.0x-SE (~95%-ish one-sided) bar, inflates the
# real family-wise false-commit rate well above the nominal per-test rate
# -- and an exhaustive 64-combination ground-truth sweep (see
# exhaustive_search.py) confirmed this concretely: 4 of 64 combinations
# cleared a plain 2.0x bar (consistent with chance alone -- ~1-2 false
# positives expected from 64 tests even if nothing were real), while the
# combination this pipeline had actually committed to in a real run
# ranked 60th of 64 under corrected measurement (delta -0.0013). A proper
# Bonferroni correction for up to MAX_ITERATIONS look-backs needs roughly
# z=2.7 for one-sided alpha=0.05/12 -- raised from 2.0 to 2.7 accordingly.
# This is an approximate, conservative bound (the per-iteration tests
# aren't fully independent, so exact family-wise control isn't claimed),
# not a precise p-value.
THRESHOLD_SE_MULTIPLIER = 2.7

# Columns confirmed to carry real (not synthetic) missing values in
# adult.csv, marked "?" in the raw data. See Documentation.md for the
# empirical F1 gap this produces.
KNOWN_MISSING_COLUMNS = ["workclass", "occupation", "native.country"]

MIN_STAGE_GAIN_FRAC = 0.25  # (2026-09-30) an op joins the chain only if it improves it by >= this fraction of its own bar (no staging on 4th-decimal noise)
MAX_ITERATIONS = 16  # (2026-09-30) raised 12 -> 16: detector-driven planning offers ~14 (column, op) pairs on real Adult; Bonferroni is re-sized to match.
# [older note follows] (2026-09-29, corrected) 9 valid (column, operation) pairs exist for
# the 3 real-missingness categorical columns (fill_mode + drop_rows + fill_unknown each,
# since fill_unknown was added) -- was previously mis-commented as 6 before fill_unknown
# existed. A single chain attempt can try at most all 9 before it must commit or be
# discarded. 12 leaves a little room beyond that, not for a full second attempt.
# NOTE: per the exhaustive ground-truth search (exhaustive_search.py), no combination of
# these operations clears a properly corrected significance bar on the real Adult Census
# '?' missingness -- "leave the data as-is" is the defensible finding on this dataset.
# MAX_ITERATIONS existing to search harder for an accept is not, by itself, evidence one
# should be found; see Documentation.md's retraction entries for the full history of why
# this comment used to (wrongly) imply the opposite.


# Explain module (2026-09-30). EXPLAIN_ENABLED: run explain.explain_run() at the
# end of pipeline.run(). EXPLAIN_USE_LLM: one Groq call for the per-iteration
# "what this means" line; every number in it is machine-checked against the
# audit log, and any line that fails the check is replaced by the deterministic
# template. Set EXPLAIN_USE_LLM=False (or run explain.py --offline) to use no LLM.
EXPLAIN_ENABLED = True
EXPLAIN_USE_LLM = True
