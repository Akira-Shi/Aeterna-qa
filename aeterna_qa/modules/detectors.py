"""
Deterministic defect detectors for AETERNA-QA (2026-09-30).

Why this exists: the profiler only reported null_pct and a naive IQR count,
so the planner had nothing to reason about except "which pair on the menu
haven't I tried". A planner can only pick the right fix if something first
tells it WHAT IS WRONG and WHERE, with evidence. These detectors do that.
They are plain pandas -- no LLM, no randomness -- so a finding is
reproducible and can be scored against a known answer key (injection.py).

Each detector returns Finding dicts:
    defect        one of DEFECT_TYPES
    column        column name, or "*" for a whole-row defect
    n_rows        rows affected
    pct           % of dataset rows affected
    evidence      short human-readable string (goes straight into the report)
    candidate_ops fixes worth VERIFYING (names of ops; verification by F1 is
                  still the only thing allowed to commit one)
    detail        machine-readable extras (sentinel value, variant groups...)

A finding is a hypothesis, not a verdict: "this looks wrong" is cheap and
can be false-positive (e.g. Adult's age==90 is real top-coding, not garbage).
Whether fixing it helps is decided later, by the fixed-fold F1 gate.
"""
import re
import pandas as pd

from . import config

DEFECT_TYPES = ["missing", "duplicates", "sentinel", "top_coded", "category_variants", "mixed_units"]

# Tunables -- declared here, not tuned per dataset.
SENTINEL_MIN_ROWS = 20          # a spike smaller than this is just a value
SENTINEL_MIN_PCT = 0.05         # ...and must be at least this % of rows
MAX_SPIKE_SHARE = 0.20          # above this a value is the column's mode, not a spike
SPIKE_RATIO = 5.0               # spike count vs median count of the next 10 distinct values
_MAGIC_NEGATIVE = {-1, -9, -99, -999, -9999}
# mixed-units detection (declared, not tuned): the upper cluster must sit past a multiplicative gap
UNIT_FACTORS = (12, 100, 1000)  # years<->months, units<->cents, k<->1
UNIT_MIN_GAP_RATIO = 1.5        # smallest jump between consecutive distinct values that counts as a gap
UNIT_MIN_ROWS = 20
UNIT_MIN_SHARE, UNIT_MAX_SHARE = 0.01, 0.50   # upper cluster size as a share of positive values
UNIT_FACTOR_TOL = 0.25          # median ratio must be within 25% of a declared factor
UNIT_MIN_DISTINCT_HI = 5        # a single repeated value is a sentinel, not a unit shift


def _is_all_nines(v) -> bool:
    try:
        return bool(re.fullmatch(r"9{2,}", str(int(abs(v)))))
    except (ValueError, TypeError):
        return False


def _pct(n: int, total: int) -> float:
    return round(100 * n / total, 3) if total else 0.0


def detect_missing(df: pd.DataFrame) -> list[dict]:
    out = []
    for col in df.columns:
        if col == config.TARGET_COLUMN:
            continue
        n = int(df[col].isna().sum())
        if n == 0:
            continue
        numeric = pd.api.types.is_numeric_dtype(df[col])
        ops = ["fill_median", "fill_mean", "drop_rows"] if numeric else ["fill_mode", "fill_unknown", "drop_rows"]
        out.append({
            "defect": "missing", "column": col, "n_rows": n, "pct": _pct(n, len(df)),
            "evidence": f"{n} null values ({_pct(n, len(df))}% of rows)",
            "candidate_ops": ops, "detail": {},
        })
    return out


def detect_duplicates(df: pd.DataFrame) -> list[dict]:
    n = int(df.duplicated().sum())
    if n == 0:
        return []
    return [{
        "defect": "duplicates", "column": "*", "n_rows": n, "pct": _pct(n, len(df)),
        "evidence": f"{n} rows are exact copies of an earlier row",
        "candidate_ops": ["dedupe_rows"], "detail": {},
    }]


def find_sentinel_value(s: pd.Series):
    """Return the sentinel value in a numeric Series (a missing-value code far
    outside the real range), or None. Used by the executor to FIT the sentinel
    from training rows only -- same rule as detect_spikes, so detection and
    repair can never disagree about what counts as a sentinel."""
    s = s.dropna()
    vc = s.value_counts()
    if len(vc) < 12:
        return None
    for v in (s.max(), s.min()):
        n = int(vc.get(v, 0))
        if n < SENTINEL_MIN_ROWS or n / len(s) > MAX_SPIKE_SHARE:
            continue
        if not (_is_all_nines(v) or v in _MAGIC_NEGATIVE):
            continue
        others = sorted([x for x in vc.index if x != v], key=lambda x: abs(x - v))
        nearest = others[0] if others else v
        if abs(v - nearest) > 0.5 * max(abs(nearest), 1.0):
            return v
    return None


def find_unit_shift(s: pd.Series):
    """Return (cut, factor) if a numeric column looks like it mixes two units
    (an upper cluster ~ a declared FACTOR times the lower cluster), else None.
    `cut` = a value above which entries are divided by `factor`. Evidence used:
    (1) a multiplicative gap between consecutive distinct values, (2) the upper
    cluster is several distinct values (not one repeated code), (3) median ratio
    matches a declared factor, (4) upper/factor lands inside the lower range.
    Shared by the detector and the executor (fit on training rows only)."""
    s = s.dropna()
    s = s[s > 0]
    if len(s) < 200 or s.nunique() < 12:
        return None
    u = s.sort_values().unique()
    ratios = u[1:] / u[:-1]
    i = int(ratios.argmax())
    if ratios[i] < UNIT_MIN_GAP_RATIO:
        return None
    lo, hi = s[s <= u[i]], s[s >= u[i + 1]]
    share = len(hi) / len(s)
    if len(hi) < UNIT_MIN_ROWS or not (UNIT_MIN_SHARE <= share <= UNIT_MAX_SHARE):
        return None
    if hi.nunique() < UNIT_MIN_DISTINCT_HI:
        return None
    ratio = float(hi.median() / lo.median())
    factor = min(UNIT_FACTORS, key=lambda k: abs(ratio - k) / k)
    if abs(ratio - factor) / factor > UNIT_FACTOR_TOL:
        return None
    if not (hi.min() / factor >= 0.9 * lo.min() and hi.max() / factor <= 1.1 * lo.max()):
        return None
    return (float(lo.max()) * UNIT_MIN_GAP_RATIO, factor)


def norm_key(x) -> str:
    return _norm_key(x)


def detect_spikes(df: pd.DataFrame) -> list[dict]:
    """Numeric columns where ONE extreme value carries far more mass than its
    neighbours. Split into two labels, because the right reaction differs:
      sentinel   -> value is an obvious missing-value code (all nines, or -1/-999):
                    it is a stand-in for 'unknown', treat as missing.
      top_coded  -> extreme value is a plausible cap (e.g. age 90): the value is
                    'this or more', not garbage; usually leave alone or clip.
    """
    out = []
    for col in df.columns:
        if col == config.TARGET_COLUMN or not pd.api.types.is_numeric_dtype(df[col]):
            continue
        s = df[col].dropna()
        vc = s.value_counts()
        if len(vc) < 12:      # low-cardinality/coded column, spikes are meaningless
            continue
        for v in (s.max(), s.min()):
            n = int(vc.get(v, 0))
            if n < SENTINEL_MIN_ROWS or _pct(n, len(df)) < SENTINEL_MIN_PCT:
                continue
            # A value holding a large share of all rows is the column's mode
            # (e.g. capital.gain == 0, 92% of rows), i.e. zero-inflation, not a spike.
            if n / len(df) > MAX_SPIKE_SHARE:
                continue
            others = sorted([x for x in vc.index if x != v], key=lambda x: abs(x - v))[:10]
            neigh_med = float(vc.loc[others].median()) if others else 1.0
            ratio = n / max(neigh_med, 1.0)
            magic = _is_all_nines(v) or (v in _MAGIC_NEGATIVE)
            # A magic-looking number is only a SENTINEL if it sits well outside the
            # real range (999 in age, 99999 in capital.gain). 99 hours/week has
            # 98 right beside it: that is a cap, not a code.
            nearest = others[0] if others else v
            far_from_data = abs(v - nearest) > 0.5 * max(abs(nearest), 1.0)
            is_sentinel = magic and far_from_data
            if not is_sentinel and ratio < SPIKE_RATIO:
                continue
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            clip_ok = (q3 - q1) > 0   # IQR==0 (e.g. 92%-zero capital.gain) -> clipping flattens the whole column
            kind = "sentinel" if is_sentinel else "top_coded"
            v_disp = int(v) if float(v).is_integer() else float(v)
            out.append({
                "defect": kind, "column": col, "n_rows": n, "pct": _pct(n, len(df)),
                "evidence": (f"value {v_disp} appears {n}x ({_pct(n, len(df))}% of rows), "
                             f"{ratio:.0f}x the typical count of its neighbours"
                             + ("; sits far outside the real range, looks like a missing-value code"
                                if is_sentinel else "; looks like a cap/top-code")),
                "candidate_ops": ((["sentinel_to_median"] if is_sentinel else []) + (["clip_outliers"] if clip_ok else [])),
                "detail": {"value": v_disp, "spike_ratio": round(ratio, 1)},
            })
    return out


def detect_mixed_units(df: pd.DataFrame) -> list[dict]:
    out = []
    for col in df.columns:
        if col == config.TARGET_COLUMN or not pd.api.types.is_numeric_dtype(df[col]):
            continue
        fit = find_unit_shift(df[col])
        if fit is None:
            continue
        cut, factor = fit
        n = int((df[col] > cut).sum())
        out.append({
            "defect": "mixed_units", "column": col, "n_rows": n, "pct": _pct(n, len(df)),
            "evidence": (f"{n} values sit above {cut:.0f}, a gap past the bulk of the column; "
                         f"dividing them by {factor} lands them inside the normal range, "
                         f"looks like a mix of two units"),
            "candidate_ops": ["rescale_units"], "detail": {"cut": cut, "factor": factor},
        })
    return out


def _norm_key(x: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(x).lower())


def detect_category_variants(df: pd.DataFrame) -> list[dict]:
    """Text columns where several distinct raw strings collapse to the same
    normalised key (case / whitespace / punctuation only). Deliberately
    conservative: it never merges genuinely different words."""
    out = []
    for col in df.columns:
        if col == config.TARGET_COLUMN or pd.api.types.is_numeric_dtype(df[col]):
            continue
        s = df[col].dropna().astype(str)
        groups: dict[str, list[str]] = {}
        for raw in s.unique():
            groups.setdefault(_norm_key(raw), []).append(raw)
        frag = {k: v for k, v in groups.items() if len(v) > 1}
        if not frag:
            continue
        affected = int(s.isin([r for v in frag.values() for r in v]).sum())
        canon_map = {}
        for k, forms in frag.items():
            counts = s[s.isin(forms)].value_counts()
            canon = counts.index[0]
            for f in forms:
                canon_map[f] = canon
        # rows whose raw form differs from the group's dominant form = rows a fix would change
        n_changed = int(s.map(lambda x: canon_map.get(x, x) != x).sum())
        out.append({
            "defect": "category_variants", "column": col, "n_rows": n_changed, "pct": _pct(n_changed, len(df)),
            "evidence": (f"{len(frag)} categories split into {sum(len(v) for v in frag.values())} spellings; "
                         f"{n_changed} rows use a non-dominant spelling"),
            "candidate_ops": ["normalize_categories"],
            "detail": {"groups": {k: v for k, v in list(frag.items())[:8]}, "canonical": canon_map},
        })
    return out


def detect(df: pd.DataFrame) -> list[dict]:
    """Run every detector. Order = severity-agnostic; ranking is a later job."""
    findings = []
    for fn in (detect_missing, detect_duplicates, detect_spikes, detect_category_variants, detect_mixed_units):
        findings.extend(fn(df))
    return findings
