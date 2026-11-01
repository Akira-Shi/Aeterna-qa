#!/usr/bin/env python3
"""Generate Documents/EXPECTED_OUTCOMES_real_data.md from the CleanML dirty-vs-clean diff only.

  python -E -P tools/make_expected_outcomes.py

Deterministic: no randomness, no timestamps, no model scores, no pipeline or evaluator import. Reads files in
Dataset/real/ (untrusted data; only pandas reads them). Applies the Q1 union rule of
Documents/AMENDMENT_DRAFT_real_data.md section D. Any row the amendment rules do not settle goes under
"Ambiguous - Akira decides"; this script never chooses for them.
"""
import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REAL = ROOT / "Dataset" / "real"
OUT = ROOT / "Documents" / "EXPECTED_OUTCOMES_real_data.md"
SPLIT_SEED = 20261101

Q1_RULE = ("Q1 union rule (amendment section D): error cells for an error type = the union, over ALL CleanML cleaned "
           "files for that error type, of the cells where dirty != clean (NaN-aware, exact comparison, positional "
           "row alignment). Matching op class: missing values -> fill_* / drop_rows; outliers -> clip_outliers; "
           "inconsistency -> normalize_categories. Column with a diff for that error type -> expected commit for "
           "the matching op class. fill_mean / fill_median on a continuous numeric column with NaN -> no commit "
           "(evaluator v1.1 median-imputes numeric NaN in every fold, section B). Column with no diff -> no commit "
           "(any commit there is an 'unexplained commit', reported separately).")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def rd(rel: str, **kw) -> pd.DataFrame:
    return pd.read_csv(REAL / rel, **kw)


def diff_cols(dirty: pd.DataFrame, clean: pd.DataFrame) -> dict:
    """Per-column count of cells where dirty != clean (both NaN counts as equal). Requires aligned shape."""
    assert dirty.shape == clean.shape and list(dirty.columns) == list(clean.columns), (dirty.shape, clean.shape)
    out = {}
    for c in dirty.columns:
        x, y = dirty[c], clean[c]
        n = int((~((x == y) | (x.isna() & y.isna()))).sum())
        if n:
            out[c] = n
    return out


def main():
    inputs = []          # (relative path, sha256)

    def use(rel):
        inputs.append((rel, sha(REAL / rel)))

    # ---------------- Airbnb ----------------
    ab_files = ["Airbnb/raw/raw.csv", "Airbnb/raw/Holoclean_mv_clean.csv",
                "Airbnb/outliers/dirty_train.csv", "Airbnb/outliers/dirty_test.csv",
                "Airbnb/outliers/clean_HC_impute_holoclean_train.csv", "Airbnb/outliers/clean_HC_impute_holoclean_test.csv",
                "Airbnb/outliers/clean_SD_impute_mean_dummy_train.csv", "Airbnb/outliers/clean_SD_impute_mean_dummy_test.csv",
                "Airbnb/raw/Holoclean_outlier_clean.csv"]
    mk_files = ["Marketing/raw/raw.csv", "Marketing/raw/Holoclean_mv_clean.csv", "Marketing/raw/orgin.csv"]
    for f in mk_files + ab_files:
        use(f)

    raw = rd("Airbnb/raw/raw.csv")
    label_ab = "Rating"
    feats_ab = [c for c in raw.columns if c != label_ab]
    num_ab = [c for c in feats_ab if pd.api.types.is_numeric_dtype(raw[c])]
    txt_ab = [c for c in feats_ab if c not in num_ab]
    mv_ab = diff_cols(raw, rd("Airbnb/raw/Holoclean_mv_clean.csv"))

    dirty = pd.concat([rd("Airbnb/outliers/dirty_train.csv"), rd("Airbnb/outliers/dirty_test.csv")], ignore_index=True)
    hc = pd.concat([rd("Airbnb/outliers/clean_HC_impute_holoclean_train.csv"),
                    rd("Airbnb/outliers/clean_HC_impute_holoclean_test.csv")], ignore_index=True)
    sd_train = rd("Airbnb/outliers/clean_SD_impute_mean_dummy_train.csv")
    sd_test = rd("Airbnb/outliers/clean_SD_impute_mean_dummy_test.csv")
    d_test = rd("Airbnb/outliers/dirty_test.csv")
    out_hc = diff_cols(dirty, hc)
    out_sd = diff_cols(d_test, sd_test)          # train file of this cleaner ships with 0 rows
    out_union = {c: (out_hc.get(c, 0), out_sd.get(c, 0)) for c in sorted(set(out_hc) | set(out_sd))}
    ho = rd("Airbnb/raw/Holoclean_outlier_clean.csv")

    # ---------------- Marketing ----------------
    mraw = rd("Marketing/raw/raw.csv", keep_default_na=False, dtype=str)
    mclean = rd("Marketing/raw/Holoclean_mv_clean.csv", keep_default_na=False, dtype=str)
    label_mk = "Income"
    feats_mk = [c for c in mraw.columns if c != label_mk]
    blanks_mk = {c: int((mraw[c] == "").sum()) for c in feats_mk}
    ok = (mraw != "").all(axis=1)
    pos_diff_mk = int((mraw != mclean).any(axis=1).sum())
    pos_diff_complete_mk = int((mraw != mclean).any(axis=1)[ok].sum())
    first_bad = int((mraw != mclean).any(axis=1)[ok].idxmax())

    # ---------------- rows ----------------
    rows = []         # (dataset, column, error type, op class, expected, evidence)
    amb = []          # (dataset, column, error type, op class, reason)

    for c in feats_ab:
        n = mv_ab.get(c, 0)
        isnum = c in num_ab
        ops = (["fill_mean", "fill_median"] if isnum else []) + ["fill_mode", "fill_unknown", "drop_rows"]
        for op in ops:
            ev = f"missing diff cells={n}"
            if n == 0:
                rows.append(("Airbnb", c, "missing", op, "no commit", ev))
            elif op in ("fill_mean", "fill_median"):
                rows.append(("Airbnb", c, "missing", op, "no commit", ev + "; continuous numeric NaN, v1.1 in-fold imputation"))
            elif isnum:
                amb.append(("Airbnb", c, "missing", op, ev + "; numeric column, op not fill_mean/fill_median: the continuous-NaN "
                            "rule does not cover it, the literal rule says commit"))
            else:
                rows.append(("Airbnb", c, "missing", op, "commit", ev))
    for c in num_ab:
        h, s = out_union.get(c, (0, 0))
        rows.append(("Airbnb", c, "outliers", "clip_outliers", "commit" if (h or s) else "no commit",
                     f"outlier diff cells: HC_impute_holoclean={h}, SD_impute_mean_dummy(test only)={s}"))
    for c in txt_ab:
        rows.append(("Airbnb", c, "inconsistency", "normalize_categories", "no commit",
                     "no CleanML inconsistency cleaned file for Airbnb; no diff"))

    for c in feats_mk:
        for op in ["fill_mode", "fill_unknown", "drop_rows"]:
            amb.append(("Marketing", c, "missing", op,
                        f"blank cells in raw.csv={blanks_mk[c]}; cleaned file not row-aligned (see note M1)"))
        rows.append(("Marketing", c, "inconsistency", "normalize_categories", "no commit",
                     "no CleanML inconsistency cleaned file for Marketing; no diff"))

    rows.sort(key=lambda r: (r[0], r[2], r[1], r[3]))
    amb.sort(key=lambda r: (r[0], r[2], r[1], r[3]))

    def counts(ds):
        r = [x for x in rows if x[0] == ds]
        return len(r), sum(1 for x in r if x[4] == "commit"), sum(1 for x in r if x[4] == "no commit")

    L = []
    L.append("# EXPECTED OUTCOMES - real data (CleanML Marketing, Airbnb)")
    L.append("")
    L.append("Generated by `tools/make_expected_outcomes.py` (script git hash: `__SCRIPT_GIT_HASH_PLACEHOLDER__`). "
             "Derived from the dirty-vs-clean diff only; no pilot or evaluation score was used. "
             "Deterministic: re-running yields a byte-identical file.")
    L.append("")
    L.append("Status: **NOT SIGNED.** No pre-registered run may start until Akira signs and this file is committed "
             "(amendment section K).")
    L.append("")
    L.append("## Generating inputs")
    L.append("")
    L.append(f"- Split seed (Akira, amendment section F): {SPLIT_SEED}")
    L.append("- Positive labels: Marketing `Income = 0`; Airbnb `Rating = Y`")
    L.append("- Evaluator: v1.1 (LR, Brier gate); op menu and detectors unchanged")
    L.append("- Airbnb `raw.csv`: 33,145 rows x 40 columns")
    L.append("- Q1 rule text, verbatim from this script:")
    L.append("")
    L.append("> " + Q1_RULE)
    L.append("")
    L.append("Input files (relative to `Dataset/real/`, sha256 of file bytes):")
    L.append("")
    L.append("| File | sha256 |")
    L.append("|---|---|")
    for rel, h in inputs:
        L.append(f"| `{rel}` | `{h}` |")
    L.append("")
    L.append("Cleaned files used per error type:")
    L.append("")
    L.append("- Marketing, missing: `Marketing/raw/Holoclean_mv_clean.csv` vs `Marketing/raw/raw.csv` - UNUSABLE for a positional diff (note M1); see Ambiguous.")
    L.append("- Marketing, outliers / inconsistency: no cleaned file ships; no rows other than the no-diff rows below.")
    L.append("- Airbnb, missing: `Airbnb/raw/Holoclean_mv_clean.csv` vs `Airbnb/raw/raw.csv` (row-aligned; diff cells equal the NaN cells per column).")
    L.append("- Airbnb, outliers: `clean_HC_impute_holoclean_{train,test}.csv` vs `dirty_{train,test}.csv` (train rows then test rows), "
             f"and `clean_SD_impute_mean_dummy_test.csv` vs `dirty_test.csv` (the SD train file ships with {len(sd_train)} rows, so only its test file is usable). "
             "Union of the two.")
    L.append("- Airbnb, inconsistency: no cleaned file ships.")
    L.append("- Airbnb, duplicates (not a row class here): CleanML ships `duplicates/` files, but the v1 op menu has no dedupe op, so no op class maps to them and no rows are generated.")
    L.append("")
    L.append("Notes:")
    L.append("")
    L.append(f"- M1: `Marketing/raw/Holoclean_mv_clean.csv` is not row-aligned to `raw.csv`: {pos_diff_mk} of 8,993 rows differ positionally, "
             f"including {pos_diff_complete_mk} of {int(ok.sum())} rows that have no blank cell in `raw.csv` (first at row index {first_bad}); "
             "the file has no index column. A positional dirty != clean diff would mark thousands of cells in every column including the label, so it is not applied.")
    L.append(f"- A1: `Airbnb/raw/Holoclean_outlier_clean.csv` ({len(ho)} rows) is not aligned to any shipped dirty file (positional diff against the outliers dirty files marks nearly every cell, including identifier-like columns), so it is not used; see Ambiguous.")
    L.append("")
    L.append("## Summary")
    L.append("")
    L.append("| Dataset | Rows in main table | Expected commit | Expected no commit | Ambiguous rows |")
    L.append("|---|---|---|---|---|")
    for ds in ("Marketing", "Airbnb"):
        t, c, n = counts(ds)
        L.append(f"| {ds} | {t} | {c} | {n} | {sum(1 for a in amb if a[0] == ds)} |")
    L.append("")
    L.append("## Expected outcomes (every row)")
    L.append("")
    L.append("| Dataset | Column | Error type | Op class | Expected | Evidence |")
    L.append("|---|---|---|---|---|---|")
    for r in rows:
        L.append("| " + " | ".join(r) + " |")
    L.append("")
    L.append("## Ambiguous - Akira decides")
    L.append("")
    L.append("The amendment rules do not settle these rows; the script did not choose. Each needs a written decision before signing.")
    L.append("")
    L.append("- **Airbnb numeric missing, op fill_mode / fill_unknown / drop_rows:** section B says drop_rows and fill_unknown are unaffected by the continuous-NaN note, "
             "but states no expectation for them; the literal Q1 hit rule gives 'commit'. fill_mode on a continuous column is also not named in the note.")
    L.append("- **Marketing missing (all 13 columns):** the only cleaned file is not row-aligned (M1), so the Q1 diff cannot be computed. "
             "Candidate alternative (not applied): treat blank cells in `raw.csv` (counts below) as the error cells.")
    L.append("- **Airbnb outliers, `Holoclean_outlier_clean.csv`:** a CleanML cleaned file that cannot be aligned (A1). Q1 says 'ALL cleaned files'; include (and how to align) or exclude?")
    L.append("- **Airbnb outliers, SD train file is empty:** only its test file contributes; confirm this is acceptable.")
    L.append("- **Duplicates:** no dedupe op exists in the menu (future work); confirm no rows are wanted.")
    L.append("")
    L.append("| Dataset | Column | Error type | Op class | Reason |")
    L.append("|---|---|---|---|---|")
    for r in amb:
        L.append("| " + " | ".join(r) + " |")
    L.append("")
    L.append("## Signature")
    L.append("")
    L.append("Signed (Akira): ______________________________    Date: ______________")
    L.append("")
    L.append("File sha256 and git commit hash: recorded in the PREREGISTRATION section 12 row, not in this file.")
    L.append("")
    OUT.write_bytes("\n".join(L).encode("utf-8"))
    print(f"wrote {OUT}")
    for ds in ("Marketing", "Airbnb"):
        print(ds, counts(ds), "ambiguous", sum(1 for a in amb if a[0] == ds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
