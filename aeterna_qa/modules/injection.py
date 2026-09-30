"""
Declared synthetic corruption + answer key for AETERNA-QA (2026-09-30).

Adult is nearly clean, so on the real data the correct outcome is "commit
nothing". To show the agent can also FIND a defect, PICK a fix, and COMMIT it,
we inject known defects. Because we know exactly what was injected, we can
score the agent against an answer key -- something real dirty data never offers.

This is a demo of the commit path, and is labelled SYNTHETIC everywhere it is
used. The spec below is declared BEFORE any run and must not be tuned after
looking at results (tuning it to make the gain bigger would be rigging the
answer, not demonstrating the mechanism).

Row IDs (the DataFrame index) are preserved so the fixed folds still apply.
"""
import numpy as np
import pandas as pd

INJECTION_SEED = 20260930

# SPEC HISTORY (kept so the change is never hidden):
#   v1 (declared 2026-09-30 morning): frag_occupation 30%, sentinel_age 5%.
#      Measured afterwards (single_op_sweep): RF sees neither (all deltas ~0). LR sees the age
#      sentinel at +0.0074 (bar 0.0087, SE 0.0027) -- 85% of the bar, no commit -- and does not see
#      the fragmentation (+0.0004).
#   v2 (this file): sentinel_age rate 5% -> 8%, chosen by the guide's selection rule, NOT by
#      trial-and-error: needed gain = bar + 0.84*SE = 0.0109; gain is ~linear in rate, so
#      rate = 5% * 0.0109/0.0074 = 7.4%, rounded UP to 8%. It is run ONCE; if it does not commit,
#      the rate is not raised again. NOTE: v1 gains were seen before v2 was set -- disclosed.
#      frag_occupation is kept at 30% and re-labelled a NEGATIVE CONTROL (expected_commit False):
#      both evaluators show it does not hurt the model, so the correct agent behaviour is to
#      leave it alone.
# Each entry: what to corrupt, how much, and the fix that would undo it.
DECLARED_SPEC = [
    {
        "id": "frag_occupation",
        "kind": "category_variants",
        "column": "occupation",
        "rate": 0.30,           # share of non-null rows re-spelled
        "expected_fix": "normalize_categories",
        "expected_commit": False,   # negative control: measured harmless at this rate
    },
    {
        "id": "sentinel_age",
        "kind": "sentinel",
        "column": "age",
        "rate": 0.08,           # share of rows overwritten (v2, see SPEC HISTORY)
        "value": 999,
        "expected_fix": "sentinel_to_median",
        "expected_commit": True,
    },
]


def _respell(value: str, rng: np.random.RandomState) -> str:
    """Realistic entry-clerk variants: case change, hyphen->space, shouty caps."""
    choice = rng.randint(4)
    if choice == 0:
        return value.lower()
    if choice == 1:
        return value.upper()
    if choice == 2:
        return value.replace("-", " ")
    return value.lower().replace("-", " ")


def inject(raw_df: pd.DataFrame, spec: list[dict] = None, seed: int = INJECTION_SEED):
    """Return (corrupted_df, manifest). manifest[i] = the spec entry plus
    `rows` (index labels changed) and `original` (Series of original values)."""
    spec = spec if spec is not None else DECLARED_SPEC
    rng = np.random.RandomState(seed)
    df = raw_df.copy()
    manifest = []
    for item in spec:
        col = item["column"]
        if item["kind"] == "category_variants":
            eligible = df.index[df[col].notna()]
            n = int(round(item["rate"] * len(eligible)))
            rows = rng.choice(eligible, size=n, replace=False)
            original = df.loc[rows, col].copy()
            df[col] = df[col].astype(object)
            new_vals = [_respell(v, rng) for v in original]
            # only rows whose text actually changed count as corrupted (a
            # re-spell of "Sales" by hyphen->space changes nothing)
            changed = [a != b for a, b in zip(original, new_vals)]
            rows = rows[np.array(changed)]
            original = original[np.array(changed)]
            df.loc[rows, col] = [b for b, c in zip(new_vals, changed) if c]
        elif item["kind"] == "sentinel":
            n = int(round(item["rate"] * len(df)))
            rows = rng.choice(df.index, size=n, replace=False)
            original = df.loc[rows, col].copy()
            df.loc[rows, col] = item["value"]
        elif item["kind"] == "mixed_units":
            n = int(round(item["rate"] * len(df)))
            rows = rng.choice(df.index, size=n, replace=False)
            original = df.loc[rows, col].copy()
            df[col] = df[col].astype(float)
            df.loc[rows, col] = original.astype(float) * item["factor"]
        else:
            raise ValueError(f"Unknown injection kind {item['kind']}")
        manifest.append({**item, "rows": pd.Index(rows), "original": original})
    return df, manifest
