"""
TaskSpec (P4, 2026-11-01): the dataset/task description that replaces Adult-specific
assumptions, so the v1 pipeline can run on any CSV.

v2 wraps v1: nothing here edits evaluator.py, config.py or study.py. The frozen evaluator and the
detectors read config.TARGET_COLUMN / POSITIVE_CLASS / DATA_PATH at call time, so a spec is applied
by temporarily setting those config attributes (`applied(spec)`, restored on exit). The gate stays
LR + Brier and exists for binary targets only; for multiclass / regression Stage 1 is detection only
and reports "gate not supported" (no gate is invented).

Numeric columns with NaN are passed through as-is: since evaluator v1.1 (2026-11-01) the LR evaluator fits a
median imputer on each fold's TRAINING rows, so the earlier workaround (few-valued numeric NaN columns recoded as
categorical, continuous ones rejected) is gone. Remaining input limit: a text column with more than
MAX_ONEHOT_LEVELS (300) distinct values is an ERROR (the evaluator one-hot encodes every text column and would
explode the matrix); exclude it with drop_columns / id_columns. This limit is kept on purpose.

Exploratory use only: results on arbitrary CSVs have no pre-registered ground truth and are never cited.
"""
from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

import pandas as pd

from . import config

TASK_TYPES = ("binary", "multiclass", "regression")
MODEL_FAMILIES = ("linear", "tree_ensemble", "distance", "neural")   # stored for Stage 2; the Stage 1 gate is always LR
GATE_TASKS = ("binary",)

MAX_FILE_MB = 50
MAX_MISSING_FRAC = 0.40
MAX_ONEHOT_LEVELS = 300     # the evaluator one-hot encodes every text column; more levels than this explodes the matrix
_ID_NAME = re.compile(r"(^|[_\s.-])(id|uuid|guid|index|idx)$|^(id|uuid|guid)([_\s.-]|$)", re.I)


class SpecError(ValueError):
    """The spec or the data it points at cannot be run."""


@dataclass(frozen=True)
class TaskSpec:
    path: str
    target: str
    task_type: str = "binary"
    positive_label: str | None = None
    model_family: str = "linear"
    id_columns: tuple = ()
    drop_columns: tuple = ()

    def __post_init__(self):
        if self.task_type not in TASK_TYPES:
            raise SpecError(f"task_type must be one of {TASK_TYPES}, got {self.task_type!r}")
        if self.model_family not in MODEL_FAMILIES:
            raise SpecError(f"model_family must be one of {MODEL_FAMILIES}, got {self.model_family!r}")
        object.__setattr__(self, "path", str(self.path))
        object.__setattr__(self, "id_columns", tuple(self.id_columns))
        object.__setattr__(self, "drop_columns", tuple(self.drop_columns))
        if self.positive_label is not None:
            object.__setattr__(self, "positive_label", str(self.positive_label).strip())

    @property
    def gate_supported(self) -> bool:
        return self.task_type in GATE_TASKS

    def to_dict(self) -> dict:
        d = asdict(self)
        d["id_columns"], d["drop_columns"] = list(self.id_columns), list(self.drop_columns)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "TaskSpec":
        extra = set(d) - set(cls.__dataclass_fields__)
        if extra:
            raise SpecError(f"unknown TaskSpec fields: {sorted(extra)}")
        return cls(**d)


def adult_spec() -> TaskSpec:
    """The v1 Adult task expressed as a spec (read from config, so it cannot drift)."""
    return TaskSpec(path=str(config.DATA_PATH), target=config.TARGET_COLUMN, task_type="binary",
                    positive_label=config.POSITIVE_CLASS)


@dataclass
class Validation:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    """Same convention as evaluator.load_raw_dataset (strip text, '?' -> NA) plus empty -> NA.
    Missing values stay real NA (never the string 'nan')."""
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == object:
            s = df[col].astype("string").str.strip()
            df[col] = s.mask(s.isin(["?", ""])).astype(object)
    return df


def _as_text(s: pd.Series) -> pd.Series:
    """Canonical text form (integer-valued floats lose the '.0'); NA stays NA."""
    if pd.api.types.is_float_dtype(s):
        nn = s.dropna()
        if len(nn) and (nn == nn.round()).all():
            s = s.astype("Int64")
    return s.astype("string").str.strip()


def validate(spec: TaskSpec, df: pd.DataFrame | None = None) -> Validation:
    """Checks that run BEFORE any evaluation. Errors stop the run; warnings are printed and recorded."""
    v = Validation()
    p = Path(spec.path)
    if not p.is_file():
        v.errors.append(f"file not found: {p}")
        return v
    mb = p.stat().st_size / 1e6
    if mb > MAX_FILE_MB:
        v.warnings.append(f"file is {mb:.0f} MB (> {MAX_FILE_MB} MB): the 5x3 CV will be slow")
    if df is None:
        df = _normalise(_read_csv(p))
    if spec.target not in df.columns:
        v.errors.append(f"target column {spec.target!r} not in CSV columns {list(df.columns)[:15]}")
        return v
    for c in (*spec.id_columns, *spec.drop_columns):
        if c not in df.columns:
            v.errors.append(f"id/drop column {c!r} not in CSV")
        if c == spec.target:
            v.errors.append(f"target {c!r} cannot be an id/drop column")
    if v.errors:
        return v
    y = _as_text(df[spec.target]).dropna()
    if len(y) == 0:
        v.errors.append("target is entirely missing")
        return v
    n_missing_y = int(df[spec.target].isna().sum())
    if n_missing_y:
        v.warnings.append(f"{n_missing_y} rows have a missing target and will be dropped")
    classes = sorted(y.unique())
    if spec.task_type == "binary":
        if len(classes) != 2:
            v.errors.append(f"binary target must have exactly 2 classes, found {len(classes)}: {classes[:8]}")
        elif spec.positive_label is not None and spec.positive_label not in classes:
            v.errors.append(f"positive_label {spec.positive_label!r} not among the target classes {classes}")
    elif spec.task_type == "multiclass" and len(classes) < 3:
        v.warnings.append(f"task_type=multiclass but the target has {len(classes)} classes")
    elif spec.task_type == "regression" and not pd.api.types.is_numeric_dtype(df[spec.target]):
        v.errors.append("task_type=regression needs a numeric target")
    if not spec.gate_supported:
        v.warnings.append(f"gate not supported for task_type={spec.task_type!r}: Stage 1 will run detection only")
    skip = {spec.target, *spec.id_columns, *spec.drop_columns}
    n = len(df)
    for c in df.columns:
        if c in skip:
            continue
        miss = df[c].isna().mean()
        if miss > MAX_MISSING_FRAC:
            v.warnings.append(f"column {c!r} is {miss:.0%} missing (> {MAX_MISSING_FRAC:.0%})")
        nun = df[c].nunique(dropna=True)
        idlike = bool(_ID_NAME.search(str(c))) or (
            n > 50 and nun >= 0.98 * df[c].notna().sum() and not pd.api.types.is_float_dtype(df[c]))
        if idlike:
            v.warnings.append(f"column {c!r} looks like an ID ({nun} distinct of {n}); pass it as an id column to exclude it")
        if not pd.api.types.is_numeric_dtype(df[c]) and nun > MAX_ONEHOT_LEVELS:
            v.errors.append(f"text column {c!r} has {nun} distinct values (> {MAX_ONEHOT_LEVELS}): the evaluator one-hot "
                            f"encodes it; exclude it with drop_columns / id_columns")
    return v


def load_dataset(spec: TaskSpec) -> tuple[pd.DataFrame, dict]:
    """Load, validate and prepare the table for the unchanged pipeline. Returns (df, prep); prep lists every
    input transformation (recorded in the audit meta). Raises SpecError on validation errors."""
    raw = _normalise(_read_csv(Path(spec.path)))
    v = validate(spec, raw)
    if not v.ok:
        raise SpecError("; ".join(v.errors))
    dropped = [*spec.id_columns, *spec.drop_columns]
    prep: dict = {"dropped_columns": dropped, "rows_dropped_missing_target": 0,
                  "warnings": list(v.warnings)}
    df = raw.drop(columns=dropped)
    ytxt = _as_text(df[spec.target])
    keep = ytxt.notna().to_numpy()
    prep["rows_dropped_missing_target"] = int((~keep).sum())
    df = df.loc[keep].reset_index(drop=True)
    if spec.task_type != "regression":
        df[spec.target] = ytxt.loc[keep].reset_index(drop=True).astype(object)
    return df, prep


@contextlib.contextmanager
def applied(spec: TaskSpec, positive_label: str | None = None):
    """Temporarily point the v1 modules at this task (config.TARGET_COLUMN / POSITIVE_CLASS / DATA_PATH).
    Restored on exit, so the Adult study is unaffected after the block."""
    saved = (config.TARGET_COLUMN, config.POSITIVE_CLASS, config.DATA_PATH, list(config.KNOWN_MISSING_COLUMNS))
    config.TARGET_COLUMN = spec.target
    config.POSITIVE_CLASS = positive_label if positive_label is not None else (spec.positive_label or "")
    config.DATA_PATH = Path(spec.path)
    config.KNOWN_MISSING_COLUMNS = []
    try:
        yield spec
    finally:
        config.TARGET_COLUMN, config.POSITIVE_CLASS, config.DATA_PATH, config.KNOWN_MISSING_COLUMNS = saved


def resolve_positive_label(spec: TaskSpec, df: pd.DataFrame) -> str:
    """Binary only. An explicit positive_label wins; otherwise the MINORITY class (ties: alphabetically
    first), recorded in the audit meta. The Brier gate is symmetric in the label choice; F1 is not."""
    if spec.positive_label is not None:
        return spec.positive_label
    counts = df[spec.target].astype(str).str.strip().value_counts()
    return sorted(counts.index, key=lambda k: (counts[k], k))[0]
