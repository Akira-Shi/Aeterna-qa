"""Stage 2 rule thresholds (P6a). Product defaults, never tuned on any study dataset.

Placed here, not in modules/config.py, because config.py is a WATCHED file (frozen_check exit 2 on any edit).
These values were fixed before any Stage 2 comparison was run. They must not be changed after seeing a result
without a written rule and a changelog entry.
"""

# |sample skewness| above this marks a numeric column as skewed.
# Rationale: |skew| > 1 is the common rule-of-thumb for "highly skewed" (e.g. in Bulmer 1979, Principles of Statistics,
# which calls |skew| > 1 highly skewed; treated here as a convention). Product default, not tuned on any study dataset.
SKEW_LIMIT = 1.0

# Categorical columns with more distinct levels than this are "high cardinality" and get capped one-hot
# (rare levels pooled into one 'infrequent' column, at most this many columns). No target encoding is used.
# Rationale: keeps the one-hot matrix narrow. Product default, not tuned on any study dataset; no literature source claimed.
HIGH_CARD = 15

# A categorical column with at least this share of missing values keeps 'missing' as its own level.
# Rationale: below this the missingness is rare enough that the most frequent level is a minimal disruption.
# Product default, not tuned on any study dataset; no literature source claimed.
MISSING_INFORMATIVE = 0.05

# smallest/largest class count below this counts as imbalanced and gets class_weight='balanced' where supported.
# Rationale: a 1:4 minority-to-majority ratio is a round-number cut-off. Product default, not tuned on any study
# dataset; no literature source claimed.
IMBALANCE_RATIO = 0.25

# Gate metrics that score predicted probabilities. class_weight='balanced' shifts predicted probabilities and degrades
# calibration, so IMB-1 is not emitted when the study gate (modules/config.GATE_METRIC) is in this set.
# Decision (Akira, 2026-11-02): bank-marketing dev set -0.0491 +/- 0.0008 neg-Brier vs default, plus the mechanism.
# Adult and Marketing were not used. Calibrating in-fold (CalibratedClassifierCV) is future work, not built.
PROBABILITY_GATES = ("brier",)
