#!/usr/bin/env python3
"""Generate Documents/EXPECTED_OUTCOMES_real_data.md from the CleanML dirty file's NaN cells and dirty-vs-clean diffs only.

  python -E -P tools/make_expected_outcomes.py

Deterministic: no randomness, no timestamps, no model scores, no pipeline or evaluator import. Reads files in
Dataset/real/ (untrusted data; only pandas reads them). Applies the rules R1-R6 of
Documents/AMENDMENT_DRAFT_real_data.md section D. Any row those rules do not settle goes under
"Ambiguous - Akira decides"; this script never chooses for them. Prints the per-file alignment test.
"""
import hashlib
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REAL = ROOT / "Dataset" / "real"
OUT = ROOT / "Documents" / "EXPECTED_OUTCOMES_real_data.md"
SPLIT_SEED = 20261101

Q1_RULE = (
    "Section D rules (Akira, 2026-11-01). (R1) Missing-value error cells = the NaN cells of the DIRTY file "
    "(`raw/raw.csv` of each dataset) as loaded by the TaskSpec loader convention: `pandas.read_csv` defaults, column names "
    "stripped, text cells stripped, and '?' and empty text mapped to NaN. Cleaned files are never used to locate "
    "missing-value errors. (R2) Reachable ops. An op counts toward an expectation only if the detector/planner menu can offer it for that column's dtype, taken from the code at commit d6ee33e (quoted in amendment section D): `detectors.detect_missing` offers fill_median, fill_mean, drop_rows on numeric columns and fill_mode, fill_unknown, drop_rows on non-numeric columns; fill_mean and fill_median are excluded from the missing-value class (section B), so a numeric NaN column has drop_rows as its only reachable op and a non-numeric NaN column has fill_mode, fill_unknown, drop_rows. clip_outliers is offered only by `detect_spikes` (numeric columns) and normalize_categories only by `detect_category_variants` (non-numeric columns); both detectors are data-dependent and are NOT evaluated here (no detector is run on CleanML data), so reachability for these two is by dtype only. Scoring unit: one row per (dataset, column, error type); Hit = any reachable op in the class commits. (R3) Outlier error cells = the union, over the CleanML outlier "
    "cleaned files that pass the alignment test, of the cells where dirty != clean (NaN-aware, exact, positional row "
    "alignment; train file rows then test file rows; a file shipped with 0 rows contributes no cells). Matching op class: "
    "clip_outliers on a numeric column with such cells -> expected 'commit', otherwise 'no commit'. (R4) Inconsistency: no "
    "CleanML inconsistency cleaned file ships for either dataset, so normalize_categories -> expected 'no commit' on every "
    "text column. (R5) Alignment test: a cleaned file is used only if its positional diff against its dirty file has the "
    "same shape and columns and is zero cells on the label column and on every identifier-like column of the dirty file. "
    "Identifier-like = the taskspec.py validate() rule: the column name matches `(^|[_\\s.-])(id|uuid|guid|index|idx)$|"
    "^(id|uuid|guid)([_\\s.-]|$)` (case-insensitive), or the file has more than 50 rows and the column's distinct count >= "
    "0.98 x its non-null count and the column is not a float dtype. 'ALL cleaned files' in Q1 means all cleaned files that "
    "pass this test. (R6) Duplicates are outside the op menu (amendment section M): no rows.")

ID_NAME = re.compile(r"(^|[_\s.-])(id|uuid|guid|index|idx)$|^(id|uuid|guid)([_\s.-]|$)", re.I)   # = taskspec._ID_NAME


def sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def rd(rel: str) -> pd.DataFrame:
    """TaskSpec loader convention (taskspec._read_csv + _normalise): read_csv defaults, stripped names, stripped text,
    '?' and empty text -> NaN."""
    df = pd.read_csv(REAL / rel)
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == object:
            t = df[col].astype("string").str.strip()
            df[col] = t.mask(t.isin(["?", ""])).astype(object)
    return df


def cat(*rels) -> pd.DataFrame:
    return pd.concat([rd(r) for r in rels], ignore_index=True)


def diff_cols(dirty: pd.DataFrame, clean: pd.DataFrame) -> dict:
    """Per-column count of cells where dirty != clean (both NaN counts as equal). Requires aligned shape."""
    out = {}
    for c in dirty.columns:
        x, y = dirty[c], clean[c]
        n = int((~((x == y) | (x.isna() & y.isna()))).sum())
        if n:
            out[c] = n
    return out


def id_like(df: pd.DataFrame, label: str) -> list:
    n = len(df)
    out = []
    for c in df.columns:
        if c == label:
            continue
        nun = df[c].nunique(dropna=True)
        if bool(ID_NAME.search(str(c))) or (n > 50 and nun >= 0.98 * df[c].notna().sum()
                                             and not pd.api.types.is_float_dtype(df[c])):
            out.append(c)
    return out


def align(name, dirty, clean, label):
    """Rule R5. Returns (record, diff-cols-or-None)."""
    rec = {"file": name, "dirty_rows": len(dirty), "clean_rows": len(clean)}
    if dirty.shape != clean.shape or list(dirty.columns) != list(clean.columns):
        rec.update(label_diff="n/a", id_cols="n/a", id_diff="n/a", ok=False,
                   why=f"shape/columns differ ({dirty.shape} vs {clean.shape})")
        return rec, None
    d = diff_cols(dirty, clean)
    ids = id_like(dirty, label)
    ld = d.get(label, 0)
    idd = {c: d.get(c, 0) for c in ids}
    ok = ld == 0 and all(v == 0 for v in idd.values())
    bad = ([f"label {label} differs in {ld} cells"] if ld else []) + [f"{c} differs in {v} cells" for c, v in idd.items() if v]
    rec.update(label_diff=ld, id_cols=",".join(ids) or "none", id_diff=sum(idd.values()), ok=ok,
               why="; ".join(bad) or "zero diff on label and identifier-like columns",
               rows_with_any_diff=int((~((dirty == clean) | (dirty.isna() & clean.isna()))).any(axis=1).sum()))
    return rec, d


def main():
    inputs = []          # (relative path, sha256)

    def use(rel):
        inputs.append((rel, sha(REAL / rel)))

    mk_files = ["Marketing/raw/raw.csv", "Marketing/raw/Holoclean_mv_clean.csv", "Marketing/raw/orgin.csv"]
    ab_files = ["Airbnb/raw/raw.csv", "Airbnb/raw/Holoclean_mv_clean.csv",
                "Airbnb/outliers/dirty_train.csv", "Airbnb/outliers/dirty_test.csv",
                "Airbnb/outliers/clean_HC_impute_holoclean_train.csv", "Airbnb/outliers/clean_HC_impute_holoclean_test.csv",
                "Airbnb/outliers/clean_SD_impute_mean_dummy_train.csv", "Airbnb/outliers/clean_SD_impute_mean_dummy_test.csv",
                "Airbnb/raw/Holoclean_outlier_clean.csv"]
    for f in mk_files + ab_files:
        use(f)

    label_ab, label_mk = "Rating", "Income"
    mraw, araw = rd("Marketing/raw/raw.csv"), rd("Airbnb/raw/raw.csv")
    feats_mk = [c for c in mraw.columns if c != label_mk]
    feats_ab = [c for c in araw.columns if c != label_ab]
    num_mk = [c for c in feats_mk if pd.api.types.is_numeric_dtype(mraw[c])]
    num_ab = [c for c in feats_ab if pd.api.types.is_numeric_dtype(araw[c])]
    nan_mk = {c: int(mraw[c].isna().sum()) for c in feats_mk}
    nan_ab = {c: int(araw[c].isna().sum()) for c in feats_ab}

    # ---- alignment test (R5), every cleaned file ----
    d_out = cat("Airbnb/outliers/dirty_train.csv", "Airbnb/outliers/dirty_test.csv")
    d_test = rd("Airbnb/outliers/dirty_test.csv")
    pairs = [
        ("Marketing", "missing", "Marketing/raw/Holoclean_mv_clean.csv", mraw, rd("Marketing/raw/Holoclean_mv_clean.csv"), label_mk),
        ("Airbnb", "missing", "Airbnb/raw/Holoclean_mv_clean.csv", araw, rd("Airbnb/raw/Holoclean_mv_clean.csv"), label_ab),
        ("Airbnb", "outliers", "Airbnb/outliers/clean_HC_impute_holoclean_{train+test}.csv", d_out,
         cat("Airbnb/outliers/clean_HC_impute_holoclean_train.csv", "Airbnb/outliers/clean_HC_impute_holoclean_test.csv"), label_ab),
        ("Airbnb", "outliers", "Airbnb/outliers/clean_SD_impute_mean_dummy_test.csv", d_test,
         rd("Airbnb/outliers/clean_SD_impute_mean_dummy_test.csv"), label_ab),
        ("Airbnb", "outliers", "Airbnb/raw/Holoclean_outlier_clean.csv", d_out,
         rd("Airbnb/raw/Holoclean_outlier_clean.csv"), label_ab),
    ]
    recs = []
    out_union = {}
    print("ALIGNMENT TEST (rule R5)")
    for ds, et, name, dirty, clean, label in pairs:
        rec, d = align(name, dirty, clean, label)
        rec["ds"], rec["et"] = ds, et
        recs.append(rec)
        print(f"  {'PASS' if rec['ok'] else 'FAIL'}  {ds}/{et}  {name}: rows dirty={rec['dirty_rows']} clean={rec['clean_rows']}, "
              f"label_diff={rec['label_diff']}, id_like={rec['id_cols']}, id_diff={rec['id_diff']}, "
              f"rows_with_any_diff={rec.get('rows_with_any_diff', 'n/a')}; {rec['why']}")
        if rec["ok"] and et == "outliers":
            for c, n in d.items():
                out_union.setdefault(c, []).append((name.split("/")[-1], n))

    # ---- rows ----
    rows = []         # (dataset, column, error type, reachable ops, expected, evidence)
    amb = []          # (dataset, column, error type, reachable ops, reason)
    # Row-listing rule (deterministic): every feature column gets a "missing" row; numeric feature columns also get an
    # "outliers" row; non-numeric feature columns also get an "inconsistency" row. Label column excluded.
    for ds, feats, nums, nans in (("Marketing", feats_mk, num_mk, nan_mk), ("Airbnb", feats_ab, num_ab, nan_ab)):
        for c in feats:
            n = nans[c]
            numeric = c in nums
            # reachable ops (code at d6ee33e): detect_missing menu minus fill_mean/fill_median (section B)
            miss_ops = ["drop_rows"] if numeric else ["fill_mode", "fill_unknown", "drop_rows"]
            rows.append((ds, c, "missing", ", ".join(miss_ops), "commit" if n else "no commit", f"NaN cells in dirty file={n}"))
            if numeric:
                u = out_union.get(c, []) if ds == "Airbnb" else []
                if u:
                    ev = "outlier diff cells (passing files): " + ", ".join(f"{f}={k}" for f, k in u)
                elif ds == "Airbnb":
                    ev = "no outlier diff cells in any passing cleaned file"
                else:
                    ev = "no outlier cleaned file ships"
                rows.append((ds, c, "outliers", "clip_outliers", "commit" if u else "no commit", ev))
            else:
                rows.append((ds, c, "inconsistency", "normalize_categories", "no commit",
                             "no CleanML inconsistency cleaned file ships; no diff"))
    rows.sort(key=lambda r: (r[0], r[2], r[1]))

    def counts(ds):
        r = [x for x in rows if x[0] == ds]
        return len(r), sum(1 for x in r if x[4] == "commit"), sum(1 for x in r if x[4] == "no commit")

    L = []
    L.append("# EXPECTED OUTCOMES - real data (CleanML Marketing, Airbnb)")
    L.append("")
    L.append("Generated by `tools/make_expected_outcomes.py` (script git hash: `__SCRIPT_GIT_HASH_PLACEHOLDER__`). "
             "Derived from the dirty file's NaN cells and the dirty-vs-clean diff only; no pilot or evaluation score was used. "
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
    L.append(f"- Marketing `raw.csv`: {len(mraw):,} rows x {mraw.shape[1]} columns; Airbnb `raw.csv`: {len(araw):,} rows x {araw.shape[1]} columns")
    L.append("- Rule text, verbatim from this script:")
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
    L.append("## Alignment test (rule R5), every cleaned file")
    L.append("")
    L.append("| Dataset | Error type | Cleaned file | Rows dirty / clean | Label diff cells | Identifier-like columns | Their diff cells | Result | Detail |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in recs:
        res = ("PASS (used)" if r["et"] == "outliers" else "PASS (not used for missing, R1)") if r["ok"] else "FAIL (excluded)"
        L.append(f"| {r['ds']} | {r['et']} | `{r['file']}` | {r['dirty_rows']} / {r['clean_rows']} | {r['label_diff']} | "
                 f"{r['id_cols']} | {r['id_diff']} | {res} | {r['why']} |")
    L.append("")
    L.append("Cleaned files used:")
    L.append("")
    L.append("- Missing values (both datasets): no cleaned file; error cells = NaN cells of the dirty `raw/raw.csv` (R1).")
    used = [r["file"] for r in recs if r["ok"] and r["et"] == "outliers"]
    L.append("- Airbnb outliers: " + ("; ".join(f"`{u}`" for u in used) if used else "none") + " (union of cells, R3).")
    L.append("- Marketing outliers / inconsistency, Airbnb inconsistency: no cleaned file ships.")
    L.append("- Duplicates: outside the v1 op menu (amendment section M); no rows.")
    L.append("")
    L.append("## Summary")
    L.append("")
    L.append("| Dataset | Rows in main table | Expected commit | Expected no commit | Ambiguous rows |")
    L.append("|---|---|---|---|---|")
    for ds in ("Marketing", "Airbnb"):
        t, c, n = counts(ds)
        L.append(f"| {ds} | {t} | {c} | {n} | {sum(1 for a in amb if a[0] == ds)} |")
    L.append("")
    L.append("## Expected outcomes (one row per dataset, column, error type)")
    L.append("")
    L.append("| Dataset | Column | Error type | Reachable ops (any one committing = hit) | Expected | Evidence |")
    L.append("|---|---|---|---|---|---|")
    for r in rows:
        L.append("| " + " | ".join(r) + " |")
    L.append("")
    L.append("## Ambiguous - Akira decides")
    L.append("")
    if amb:
        L.append("| Dataset | Column | Error type | Reachable ops | Reason |")
        L.append("|---|---|---|---|---|")
        for r in amb:
            L.append("| " + " | ".join(r) + " |")
    else:
        L.append("None. Rules R1-R6 settle every row.")
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
        print(ds, "(rows, commit, no commit) =", counts(ds), "ambiguous", sum(1 for a in amb if a[0] == ds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
