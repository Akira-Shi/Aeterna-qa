"""
Explain module for AETERNA-QA (added 2026-09-30, guide priority).

Turns one audit log (logs/run_*.json) into a demo-ready explanation:
a console table (rich, if installed) and a self-contained HTML report.

Design rule (BUILD_PLAN Phase 6): the explanation may QUOTE numbers from the
audit log, never generate its own. Three layers, kept visibly separate:

  1. VERDICT   -- deterministic. COMMIT / ROLLBACK and the delta-vs-bar text are
                  built from the logged numbers by code. No LLM involved. The
                  pipeline's decision is `delta >= threshold`; the explanation
                  can never disagree with it because it is derived from it.
  2. PLANNER   -- the planner's own stated reason, quoted verbatim. It was
                  written BEFORE the evaluation, so it is shown as a
                  hypothesis, not as an explanation of the result.
  3. NOTE      -- one Groq call per run: a one-sentence plain-English reading of
                  "does the measurement support the planner's reason?". Every
                  number and every column/operation identifier in that sentence
                  is machine-checked against the log. A note that fails the
                  check is DROPPED (the report says so); it is never repaired
                  or shown.

Only the NOTE layer uses an LLM. `--offline` (or config.EXPLAIN_USE_LLM=False,
or no GROQ_API_KEY, or a failed call) yields the full report minus notes.

Usage:
    python -m modules.explain                    # newest logs/run_*.json
    python -m modules.explain logs/run_X.json    # a specific run
    python -m modules.explain --offline          # no Groq call
"""
import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from . import config

# --------------------------------------------------------------------------
# Facts: everything below is derived from the log by code, no LLM.
# --------------------------------------------------------------------------


def _ops_str(ops: dict | None) -> str:
    if not ops:
        return "(none)"
    return ", ".join(f"{c}={o}" for c, o in ops.items())


def _ratio(delta, threshold):
    if delta is None or not threshold or threshold <= 0:
        return None
    return delta / threshold


def _z(delta, se):
    if delta is None or not se or se <= 0:
        return None
    return delta / se


def load_run(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def latest_log() -> Path:
    logs = sorted(Path(config.LOG_DIR).glob("run_*.json"))
    if not logs:
        raise FileNotFoundError(f"No run_*.json in {config.LOG_DIR}")
    return logs[-1]


def build_facts(run: dict) -> dict:
    """Group iterations by chain and attach the deterministic verdict to each."""
    its = [dict(i) for i in run.get("iterations", [])]
    legacy = any(i.get("column") is not None and i.get("chain_ops") is None for i in its)

    chains: dict[int, dict] = {}
    for it in its:
        cid = it.get("chain_id")
        ch = chains.setdefault(cid, {"chain_id": cid, "iterations": [], "status": None,
                                     "ops": None, "commit_iter": None})
        ch["iterations"].append(it)
        it["own_clears"] = (it.get("delta") is not None and it.get("threshold") is not None
                            and it["delta"] >= it["threshold"])
        it["ratio"] = _ratio(it.get("delta"), it.get("threshold"))
        it["z"] = _z(it.get("delta"), it.get("se"))

    for ch in chains.values():
        statuses = [i.get("status") for i in ch["iterations"]]
        evaluated = [i for i in ch["iterations"] if i.get("delta") is not None]
        if "committed" in statuses:
            ch["status"] = "committed"
        elif evaluated and "staged" in statuses:
            ch["status"] = "unresolved"
        elif evaluated:
            ch["status"] = "discarded"
        else:
            ch["status"] = "no_evaluation"
        with_ops = [i for i in ch["iterations"] if i.get("chain_ops")]
        ch["ops"] = with_ops[-1]["chain_ops"] if with_ops else None
        if ch["status"] == "committed":
            clears = [i["iteration"] for i in evaluated if i["own_clears"]]
            ch["commit_iter"] = clears[-1] if clears else None

    for ch in chains.values():
        for it in ch["iterations"]:
            it["verdict"] = _verdict(it, ch)

    committed_ops: dict = {}
    for ch in chains.values():
        if ch["status"] == "committed" and ch["ops"]:
            committed_ops.update(ch["ops"])
    # Older logs (before chain_ops was recorded) cannot say WHICH ops a committed
    # chain held. Flag that instead of presenting an empty set as "(none)".
    ops_recorded = all(bool(c["ops"]) for c in chains.values() if c["status"] == "committed")

    evaluated_all = [i for i in its if i.get("delta") is not None and i.get("ratio") is not None]
    closest = max(evaluated_all, key=lambda i: i["ratio"]) if evaluated_all else None
    n_committed = sum(1 for c in chains.values() if c["status"] == "committed")
    n_eval_chains = sum(1 for c in chains.values() if c["status"] != "no_evaluation")

    return {
        "run": run,
        "legacy": legacy,
        "chains": [chains[k] for k in sorted(chains, key=lambda x: (x is None, x))],
        "iterations": its,
        "baseline": run.get("baseline_f1"),
        "final": run.get("final_f1"),
        "committed_ops": committed_ops,
        "committed_ops_recorded": ops_recorded,
        "n_committed": n_committed,
        "n_chains": n_eval_chains,
        "n_evaluations": len(evaluated_all),
        "closest": closest,
        "metric": {"brier": "neg-Brier", "f1": "F1"}.get((run.get("meta") or {}).get("metric"), "F1"),
        "label": (run.get("meta") or {}).get("label") or "Scenario not labelled (log predates the label field)",
        "scenario": (run.get("meta") or {}).get("scenario"),
    }


def _verdict(it: dict, ch: dict) -> dict:
    """Deterministic verdict. code in {commit, commit_with_chain, rollback,
    noise, unresolved, no_eval}."""
    if it.get("delta") is None:
        err = it.get("error") or "no result"
        return {"code": "no_eval", "text": f"NOT EVALUATED - {err}"}
    d, thr, se = it["delta"], it["threshold"], it.get("se")
    z = it["z"]
    z_txt = f", {z:.1f} SE" if z is not None else ""
    if it.get("status") == "committed" and it["own_clears"]:
        return {"code": "commit",
                "text": f"COMMIT - delta {d:+.4f} cleared the bar {thr:.4f}{z_txt}"}
    if it.get("status") == "committed":
        k = ch.get("commit_iter")
        return {"code": "commit_with_chain",
                "text": (f"STAGED, then COMMITTED with its chain - alone delta {d:+.4f} was below "
                         f"the bar {thr:.4f}; the chain cleared it at iteration {k}")}
    if it.get("status") == "staged":
        return {"code": "unresolved",
                "text": f"STAGED (run ended before this chain resolved) - delta {d:+.4f}, bar {thr:.4f}"}
    if d <= 0:
        return {"code": "rollback",
                "text": f"ROLLBACK - delta {d:+.4f}: not better than the baseline (bar {thr:.4f})"}
    r = it["ratio"]
    return {"code": "noise",
            "text": (f"ROLLBACK - delta {d:+.4f} is {r:.0%} of the {thr:.4f} bar{z_txt}: "
                     f"not distinguishable from noise")}


def headline(facts: dict) -> str:
    b, f = facts["baseline"], facts["final"]
    if b is None or f is None:
        return "Run did not complete (no baseline/final F1 recorded)."
    if facts["n_committed"] == 0:
        s = (f"{facts['n_chains']} chain(s), {facts['n_evaluations']} evaluations: nothing cleared the "
             f"statistical bar -> data left as-is. {facts['metric']} {b:.4f} -> {f:.4f} (unchanged).")
        c = facts["closest"]
        if c and c.get("ratio") is not None and c["ratio"] > 0:
            s += (f" Closest miss: iteration {c['iteration']} at {c['ratio']:.0%} of its bar "
                  f"(delta {c['delta']:+.4f}, bar {c['threshold']:.4f}).")
        return s
    ops_txt = (_ops_str(facts["committed_ops"]) if facts["committed_ops_recorded"]
               else "committed operations not recorded in this older log")
    return (f"{facts['n_committed']} of {facts['n_chains']} chain(s) committed "
            f"({ops_txt}). {facts['metric']} {b:.4f} -> {f:.4f} ({f - b:+.4f}).")


# --------------------------------------------------------------------------
# Number / identifier guard for LLM notes.
# --------------------------------------------------------------------------

_NUM_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(%?)")
_IDENT_RE = re.compile(r"\b[A-Za-z_]+(?:\.[A-Za-z_]+)+\b")  # dotted names like native.country


def _numbers_in(text: str) -> set:
    return {m.group(1) for m in _NUM_RE.finditer(text or "")}


def _allowed_for_iteration(it: dict, facts: dict) -> tuple[list, set, set]:
    """(allowed floats, allowed ints, allowed identifiers) for one iteration's note."""
    floats = []
    for k in ("f1_before", "f1_after", "delta", "threshold", "se", "std_before", "std_after"):
        v = it.get(k)
        if v is not None:
            floats.append(abs(v))
    if it.get("ratio") is not None:
        floats += [abs(it["ratio"]), abs(it["ratio"]) * 100]
    if it.get("z") is not None:
        floats.append(abs(it["z"]))
    for k in ("baseline", "final"):
        if facts.get(k) is not None:
            floats.append(abs(facts[k]))
    ints = {it["iteration"]}
    if it.get("chain_id") is not None:
        ints.add(it["chain_id"])
    ints |= {len(it.get("chain_ops") or {}), len(it.get("committed_ops") or {})}
    idents = set()
    for d in (it.get("chain_ops") or {}, it.get("committed_ops") or {}):
        idents |= set(d.keys()) | set(d.values())
    if it.get("column"):
        idents.add(it["column"])
    if it.get("operation"):
        idents.add(it["operation"])
    # numbers the planner itself wrote in its reason are in the log, so quoting them is legitimate
    for tok in _numbers_in(it.get("reason") or ""):
        if "." in tok:
            floats.append(float(tok))
        else:
            ints.add(int(tok))
    return floats, ints, idents


_SNAKE_RE = re.compile(r"\b[a-z]+(?:_[a-z]+)+\b")  # operation names like fill_mode
_COLS_CACHE: list | None = None


def _dataset_columns() -> list:
    """Column names from the dataset header (cheap, cached). Empty if unreadable."""
    global _COLS_CACHE
    if _COLS_CACHE is None:
        try:
            with open(config.DATA_PATH, encoding="utf-8") as fh:
                _COLS_CACHE = [c.strip() for c in (x.strip().strip(chr(34)).strip(chr(39)) for x in fh.readline().split(",")) if c]
        except Exception:  # noqa: BLE001
            _COLS_CACHE = []
    return _COLS_CACHE


def _identifier_problems(text: str, idents: set) -> list[str]:
    """Any dataset column or operation name in `text` that this iteration/run did not test."""
    problems = [f"identifier {x} not tested here" for x in _IDENT_RE.findall(text or "") if x not in idents]
    problems += [f"operation {x} not tested here" for x in _SNAKE_RE.findall(text or "")
                 if x not in idents and x in set(config.OPERATION_MENU) | {"normalize_categories"}]
    low = (text or "").lower()
    for col in _dataset_columns():
        if "." in col or col == config.TARGET_COLUMN:
            continue  # dotted names are covered by _IDENT_RE; the target word is ordinary prose
        if col not in idents and re.search(rf"\b{re.escape(col.lower())}\b", low):
            problems.append(f"column {col} not tested here")
    return problems


def guard_note(text: str, it: dict, facts: dict) -> list[str]:
    """Return a list of problems (empty = note passes)."""
    problems = []
    floats, ints, idents = _allowed_for_iteration(it, facts)
    for m in _NUM_RE.finditer(text or ""):
        tok, pct = m.group(1), m.group(2)
        if "." in tok or pct:
            x = float(tok)
            d = len(tok.split(".")[1]) if "." in tok else 0
            tol = 0.5 * 10 ** (-d) + 1e-9
            if not any(abs(x - a) <= tol for a in floats):
                problems.append(f"number {tok}{pct} not in log")
        else:
            if int(tok) not in ints:
                problems.append(f"number {tok} not in log")
    problems += _identifier_problems(text, idents)
    return problems


# --------------------------------------------------------------------------
# LLM layer (one Groq call per run). Injectable for tests.
# --------------------------------------------------------------------------

_SYSTEM = """You annotate an audit report for an automated data-cleaning agent. \
For each iteration you are given: the cleaning operation that was tested, the \
planner's stated reason (written BEFORE any measurement), and the measured result \
(delta in the gate score vs the current baseline, the significance bar, and the verdict, which was \
computed by code).

For each iteration write ONE sentence, at most 30 words, describing what the measurement \
shows. The planner's reason is a hypothesis about what the defect is, NOT a promise of a score \
gain: say 'contradicts' only if the reason explicitly predicted an improvement. Also write a 'summary' of at most two \
sentences about what the whole run shows.

Hard rules: use ONLY numbers that appear in the input; never invent numbers, percentages, \
columns or operations; do not restate COMMIT/ROLLBACK; do not claim an operation 'helps' or \
'causes' anything beyond what the delta shows; a delta below its bar is noise, not a small win; \
plain language for a non-statistician."""


def _groq_interpret(payload: dict) -> dict:
    from groq import Groq  # lazy: offline mode must not need the package
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set")
    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "iterations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"iteration": {"type": "integer"}, "note": {"type": "string"}},
                    "required": ["iteration", "note"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["summary", "iterations"],
        "additionalProperties": False,
    }
    resp = Groq(api_key=config.GROQ_API_KEY).chat.completions.create(
        model=config.MODEL_NAME,
        messages=[{"role": "system", "content": _SYSTEM},
                  {"role": "user", "content": json.dumps(payload)}],
        response_format={"type": "json_schema",
                         "json_schema": {"name": "audit_notes", "schema": schema, "strict": True}},
        temperature=0.2,
        max_completion_tokens=4096,  # (2026-09-30) 16 iterations were truncated at the default limit
    )
    return json.loads(resp.choices[0].message.content)


def add_notes(facts: dict, interpret_fn=None) -> dict:
    """Call the LLM once, guard every note, attach survivors. Returns stats."""
    stats = {"mode": "llm", "requested": 0, "verified": 0, "rejected": [], "error": None}
    evaluated = [i for i in facts["iterations"] if i.get("delta") is not None]
    if not evaluated:
        stats["mode"] = "template-only"
        return stats
    payload = {"iterations": [{
        "iteration": i["iteration"],
        "operation_tested": {"column": i["column"], "operation": i["operation"]},
        "chain_ops_at_evaluation": i.get("chain_ops"),
        "planner_reason": i.get("reason"),
        "delta": i["delta"], "metric": facts.get("metric", "score"), "bar": i["threshold"], "se": i.get("se"),
        "verdict_computed_by_code": i["verdict"]["text"],
    } for i in evaluated]}
    stats["requested"] = len(evaluated)
    try:
        out = (interpret_fn or _groq_interpret)(payload)
    except Exception as e:  # noqa: BLE001 -- any failure -> template-only, never break the run
        stats["mode"] = "template-only"
        stats["error"] = f"{type(e).__name__}: {e}"
        return stats

    by_iter = {i["iteration"]: i for i in evaluated}
    seen = set()
    for item in out.get("iterations", []):
        n, note = item.get("iteration"), (item.get("note") or "").strip()
        it = by_iter.get(n)
        if it is None or n in seen or not note:
            stats["rejected"].append({"iteration": n, "why": ["unknown/duplicate/empty"], "note": note})
            continue
        seen.add(n)
        problems = guard_note(note, it, facts)
        if problems:
            stats["rejected"].append({"iteration": n, "why": problems, "note": note})
        else:
            it["note"] = note
            stats["verified"] += 1
    summary = (out.get("summary") or "").strip()
    if summary:
        # summary may quote any per-iteration number, baseline/final, or counts in the headline
        floats = set()
        for i in evaluated:
            fl, _, _ = _allowed_for_iteration(i, facts)
            floats |= set(fl)
        ints = {len(facts["chains"]), facts["n_chains"], facts["n_evaluations"],
                facts["n_committed"], len(evaluated)} | {i["iteration"] for i in evaluated}
        ints |= {c["chain_id"] for c in facts["chains"] if c["chain_id"] is not None}
        idents = {x for i in evaluated for x in ([i["column"], i["operation"]] +
                  list((i.get("chain_ops") or {}).keys()) + list((i.get("chain_ops") or {}).values()))
                  if x}
        bad = []
        for m in _NUM_RE.finditer(summary):
            tok, pct = m.group(1), m.group(2)
            if "." in tok or pct:
                d = len(tok.split(".")[1]) if "." in tok else 0
                if not any(abs(float(tok) - a) <= 0.5 * 10 ** (-d) + 1e-9 or
                           abs(float(tok) - 100 * a) <= 0.5 * 10 ** (-d) + 1e-9 for a in floats):
                    bad.append(f"number {tok}{pct} not in log")
            elif int(tok) not in ints:
                bad.append(f"number {tok} not in log")
        bad += _identifier_problems(summary, idents)
        if bad:
            stats["rejected"].append({"iteration": "summary", "why": bad, "note": summary})
        else:
            facts["summary_note"] = summary
    return stats


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def render_console(facts: dict, stats: dict) -> None:
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
    except ImportError:
        return _render_plain(facts, stats)

    con = Console()
    style_for = {"commit": "bold green", "commit_with_chain": "green", "rollback": "red",
                 "noise": "yellow", "unresolved": "cyan", "no_eval": "dim"}
    lab = facts["label"]
    lab_style = "bold black on yellow" if (facts.get("scenario") or "").startswith("synthetic") else "bold white on blue"
    con.print()
    con.print(Text(f" {lab} ", style=lab_style))
    body = Text(headline(facts), style="bold")
    if facts.get("summary_note"):
        body.append("\n\n" + facts["summary_note"], style="italic")
    con.print(Panel(body, title="AETERNA-QA - what the agent did and why", border_style="cyan"))
    if facts["legacy"]:
        con.print("[dim]Older log: chain contents were not recorded, so each delta is the cumulative "
                  "chain result attributed to the last-added operation.[/dim]")

    for ch in facts["chains"]:
        ops = _ops_str(ch["ops"]) if ch["ops"] else "(chain contents not recorded)"
        st = {"committed": "[bold green]COMMITTED[/]", "discarded": "[red]DISCARDED[/]",
              "unresolved": "[cyan]UNRESOLVED[/]", "no_evaluation": "[dim]NO EVALUATION[/]"}[ch["status"]]
        t = Table(title=f"Chain {ch['chain_id']}: {ops} -> {st}", title_justify="left",
                  show_lines=False, expand=False)
        t.add_column("#", justify="right")
        t.add_column("Tested")
        t.add_column("Delta", justify="right")
        t.add_column("Bar", justify="right")
        t.add_column("Result")
        if stats["verified"]:
            t.add_column("What it means", overflow="fold", max_width=48)
        for it in ch["iterations"]:
            v = it["verdict"]
            delta = f"{it['delta']:+.4f}" if it.get("delta") is not None else "-"
            bar = f"{it['threshold']:.4f}" if it.get("threshold") is not None else "-"
            tested = f"{it['column']}: {it['operation']}" if it.get("column") else "-"
            row = [str(it["iteration"]), tested, delta, bar,
                   Text(v["text"].split(" - ")[0] + (f" ({it['ratio']:.0%} of bar)" if v["code"] == "noise" else ""),
                        style=style_for[v["code"]])]
            if stats["verified"]:
                row.append(it.get("note", ""))
            t.add_row(*row)
        con.print(t)
    if stats.get("rejected"):
        con.print(f"[dim]{len(stats['rejected'])} LLM note(s) rejected by the number/identifier check "
                  f"and omitted; see the HTML report.[/dim]")
    if stats.get("error"):
        con.print(f"[dim]LLM notes unavailable ({stats['error']}); verdicts above are code-derived.[/dim]")


def _render_plain(facts: dict, stats: dict) -> None:
    print(f"\n[{facts['label']}]\n{headline(facts)}")
    if facts.get("summary_note"):
        print(facts["summary_note"])
    for ch in facts["chains"]:
        print(f"\nChain {ch['chain_id']}: {_ops_str(ch['ops']) if ch['ops'] else '(not recorded)'} -> {ch['status'].upper()}")
        for it in ch["iterations"]:
            print(f"  {it['iteration']:>2}  {it.get('column')}: {it.get('operation')}  {it['verdict']['text']}")
            if it.get("note"):
                print(f"      {it['note']}")


_CSS = """
:root{--bg:#0b1030;--card:#141b45;--ink:#eef2ff;--mute:#9fb0e0;--line:#2b3677;--good:#6fe3d0;--bad:#ff8fa3;
--warn:#f5d77a;--info:#8fd3ff;--track:#222c63;--accent:#e8c872}
*{box-sizing:border-box}body{margin:0;color:var(--ink);
background:radial-gradient(1200px 600px at 50% -10%,#26337f 0%,#0b1030 60%) fixed,var(--bg);
font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1000px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:22px;margin:4px 0 4px;color:var(--accent);letter-spacing:.04em}h2{font-size:17px;margin:0}
.sub{color:var(--mute);font-size:13px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:12px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.stat b{display:block;font-size:20px;color:var(--accent)}.stat span{color:var(--mute);font-size:12px}
.chain{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:14px 0;overflow:hidden}
.chain>header{padding:12px 16px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between}
.pill{padding:2px 10px;border-radius:999px;font-size:12px;font-weight:700;color:#0b1030}
.pill.committed{background:var(--good)}.pill.discarded{background:var(--bad)}.pill.other{background:var(--mute)}
table{width:100%;border-collapse:collapse}th,td{padding:9px 12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line);font-size:14px}
th{color:var(--mute);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.03em}
tr:last-child td{border-bottom:none}
.quote{color:var(--mute);font-style:italic}.tiny{font-size:12px;color:var(--mute)}
.v-commit,.v-commit_with_chain{color:var(--good);font-weight:600}.v-rollback{color:var(--bad);font-weight:600}
.v-noise{color:var(--warn);font-weight:600}.v-unresolved,.v-no_eval{color:var(--mute);font-weight:600}
.gauge{position:relative;height:12px;background:var(--track);border-radius:6px;min-width:150px}
.gauge .zero{position:absolute;left:50%;top:-2px;bottom:-2px;width:1px;background:var(--mute)}
.gauge .fill{position:absolute;top:2px;bottom:2px;border-radius:4px}
.gauge .tick{position:absolute;top:-3px;bottom:-3px;width:2px;background:var(--accent)}
.note{border-left:3px solid var(--accent);padding-left:8px;margin-top:6px;font-size:13px}
.foot{color:var(--mute);font-size:12px;margin-top:24px}
details{margin-top:14px}summary{cursor:pointer;color:var(--mute)}
@media (max-width:720px){th:nth-child(3),td:nth-child(3){display:none}}
"""


_CSS_PLAIN = """
.lead{background:linear-gradient(135deg,#1c2766,#141b45);border:1px solid var(--accent);border-radius:12px;padding:20px 22px;margin:14px 0}
.lead h2{font-size:22px;line-height:1.35;margin:0 0 8px}.lead p{margin:6px 0;font-size:16px}
.lead .sum{color:var(--mute);font-style:italic}
h3.sec{font-size:18px;margin:26px 0 10px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--accent);border-radius:10px;padding:14px 16px}
.card b{display:block;font-size:16px;margin-bottom:6px}.card .impact{color:var(--good);font-weight:600}
ul.undone{padding-left:20px;margin:10px 0}ul.undone li{margin:8px 0}
dl.gloss dt{font-weight:600;margin-top:10px}dl.gloss dd{margin:2px 0 0;color:var(--mute)}
.ctx{color:var(--mute);font-size:14px}
"""

_OP_PLAIN = {
    "fill_mean": "Filled in missing values in {c} with the average value",
    "fill_median": "Filled in missing values in {c} with the typical (middle) value",
    "fill_mode": "Filled in missing values in {c} with the most common value",
    "fill_unknown": "Filled in missing values in {c} with an \"Unknown\" label",
    "drop_rows": "Removed rows that had problems in {c}",
    "clip_outliers": "Pulled extreme values in {c} back toward the normal range",
    "sentinel_to_median": "Replaced placeholder values in {c} with the typical value",
    "normalize_categories": "Merged different spellings of the same category in {c}",
    "rescale_units": "Converted mixed units in {c} to one consistent unit",
    "dedupe_rows": "Removed duplicate rows",
}


def plain_fix(column, op) -> str:
    """Plain-English sentence for one (column, operation); safe for unknown ops."""
    col = str(column)
    if column is None and op is None:
        return "Looked for another fix to try"
    tpl = _OP_PLAIN.get(str(op))
    if tpl is None:
        return f"Applied an automatic clean-up to {col}"
    return tpl.format(c=col)


def _plain_undone_reason(code: str) -> str:
    return {
        "rollback": "it did not make the predictions any better",
        "noise": "the improvement was not big enough to be sure it was real",
        "unresolved": "the run ended before a decision was reached",
        "no_eval": "it could not be checked",
    }.get(code, "it did not clearly help")


def _plain_impact(it: dict | None) -> str:
    if not it or it.get("ratio") is None:
        return "prediction accuracy improved (size not recorded)"
    return ("prediction accuracy improved noticeably" if it["ratio"] >= 3
            else "prediction accuracy improved slightly")


def _plain_summary(facts: dict) -> tuple[str, str]:
    """(headline, overall sentence) in plain words. Derived from counts and
    baseline/final only; never overstates."""
    its = [i for i in facts["iterations"] if i.get("column") is not None or i.get("operation") is not None]
    n = len(its)
    kept_chain = {c["chain_id"] for c in facts["chains"] if c["status"] == "committed"}
    k = sum(1 for i in its if i.get("chain_id") in kept_chain)
    b, f = facts["baseline"], facts["final"]
    if n == 0:
        return "No fixes were tried in this run.", ""
    head = (f"We checked {n} possible fix{'es' if n != 1 else ''} to your data. "
            f"{k} {'was' if k == 1 else 'were'} kept"
            + (", the rest were undone because they did not clearly help." if n - k else "."))
    if k == 0:
        head = (f"We checked {n} possible fix{'es' if n != 1 else ''} to your data. "
                "None were kept, because none of them clearly helped.")
    if b is None or f is None:
        overall = "This run did not finish, so overall quality could not be compared."
    elif k == 0 or f == b:
        overall = "Overall, data quality was not changed: the data was left as it was."
    elif f > b:
        overall = ("Overall, the checks suggest the data is somewhat cleaner: predictions built on "
                   "it were more accurate in our cross-checked test. This is evidence, not proof.")
    else:
        overall = "Overall, the checks did not show an improvement."
    return head, overall


def render_html(facts: dict, stats: dict, source: Path) -> str:
    e = html.escape
    scale = max([abs(i["delta"]) for i in facts["iterations"] if i.get("delta") is not None] +
                [i["threshold"] for i in facts["iterations"] if i.get("threshold") is not None] + [1e-4]) * 1.15
    head, overall = _plain_summary(facts)
    out = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
           f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>AETERNA-QA Data Cleaning Report</title><style>{_CSS}{_CSS_PLAIN}</style></head><body><main>"]
    out.append("<h1>Data cleaning report</h1>")
    out.append(f"<div class='lead'><h2>{e(head)}</h2><p>{e(overall)}</p>")
    if facts.get("summary_note"):
        out.append(f"<p class='sum'>Assistant's note: {e(facts['summary_note'])}</p>")
    out.append("</div>")

    # ---- What was fixed
    kept = [c for c in facts["chains"] if c["status"] == "committed"]
    out.append("<h3 class='sec'>What was fixed</h3>")
    if not kept:
        out.append("<p class='ctx'>Nothing was changed. Your data was left exactly as it was.</p>")
    else:
        out.append("<div class='cards'>")
        for ch in kept:
            ci = ch.get("commit_iter")
            it = next((i for i in ch["iterations"] if i["iteration"] == ci), None)
            impact = _plain_impact(it)
            if ch["ops"]:
                for col, op in ch["ops"].items():
                    note = next((i["note"] for i in ch["iterations"]
                                 if i.get("note") and i.get("column") == col), None)
                    out.append(f"<div class='card'><b>{e(plain_fix(col, op))}</b>"
                               f"<span class='impact'>Effect: {e(impact)}</span>"
                               + (f"<div class='tiny'>Assistant's note: {e(note)}</div>" if note else "")
                               + "</div>")
            else:
                n_it = len([i for i in ch["iterations"] if i.get("delta") is not None])
                out.append(f"<div class='card'><b>{'A group of ' + str(n_it) + ' fixes was' if n_it > 1 else 'A fix was'} kept</b>"
                           "<span class='impact'>Effect: " + e(impact) + "</span>"
                           "<div class='tiny'>Which fix exactly was not recorded in this older log.</div></div>")
        out.append("</div>")
        if len(kept) and any(c["ops"] and len(c["ops"]) > 1 for c in kept):
            out.append("<p class='tiny'>Fixes in the same group were judged together, so the effect shown "
                       "applies to the group.</p>")

    # ---- What was tried but undone
    undone = [(c, i) for c in facts["chains"] if c["status"] != "committed" for i in c["iterations"]
              if i.get("column") is not None or i.get("operation") is not None]
    if undone:
        out.append(f"<details><summary><b>What was tried but undone ({len(undone)})</b></summary>"
                   "<ul class='undone'>")
        for c, i in undone:
            out.append(f"<li>{e(plain_fix(i.get('column'), i.get('operation')))}. Undone: "
                       f"{e(_plain_undone_reason(i['verdict']['code']))}."
                       + (f" <span class='tiny'>Assistant's note: {e(i['note'])}</span>" if i.get("note") else "")
                       + "</li>")
        out.append("</ul></details>")

    # ---- Glossary
    out.append("<details><summary><b>Key terms</b></summary><dl class='gloss'>"
               + ("<dt>Brier score</dt><dd>Prediction error. Lower is better.</dd>"
                  if facts["metric"] == "neg-Brier" else
                  "<dt>F1 score</dt><dd>Hit quality. Higher is better.</dd>") +
               "<dt>Commit</dt><dd>Fix kept.</dd><dt>Rollback</dt><dd>Fix undone.</dd></dl></details>")

    # ---- Technical details (single collapsed section)
    out.append("<details><summary><b>Technical details</b></summary>")
    b, f = facts["baseline"], facts["final"]
    if b is not None and f is not None:
        out.append("<div class='stats'>"
                   f"<div class='stat'><span>Baseline score ({e(facts['metric'])})</span><b>{b:.4f}</b></div>"
                   f"<div class='stat'><span>Final score ({e(facts['metric'])})</span><b>{f:.4f}</b></div>"
                   f"<div class='stat'><span>Chains tried</span><b>{facts['n_chains']}</b></div>"
                   f"<div class='stat'><span>Evaluations</span><b>{facts['n_evaluations']}</b></div>"
                   f"<div class='stat'><span>Chains committed</span><b>{facts['n_committed']}</b></div></div>")
    out.append(f"<p class='tiny'>{e(headline(facts))}</p>")
    out.append(f"<div class='sub'>Source: {e(source.name)} &middot; started {e(str(facts['run'].get('started_at','')))}</div>")
    if facts["legacy"]:
        out.append("<p class='tiny'>Older log: chain contents were not recorded, so each delta is the cumulative "
                   "chain result, attributed here to the last-added operation.</p>")
    for ch in facts["chains"]:
        cls = {"committed": "committed", "discarded": "discarded"}.get(ch["status"], "other")
        ops = _ops_str(ch["ops"]) if ch["ops"] else "chain contents not recorded"
        out.append(f"<section class='chain'><header><h2>Chain {ch['chain_id']} &middot; "
                   f"<span class='tiny'>{e(ops)}</span></h2><span class='pill {cls}'>{e(ch['status'].upper())}</span></header>"
                   "<table><thead><tr><th>#</th><th>Tested</th><th>Planner said (before measuring)</th>"
                   "<th>Measured vs bar</th><th>Verdict</th></tr></thead><tbody>")
        for it in ch["iterations"]:
            v = it["verdict"]
            tested = f"<b>{e(str(it.get('column')))}</b> &rarr; {e(str(it.get('operation')))}"
            others = {k: o for k, o in (it.get("chain_ops") or {}).items() if k != it.get("column")}
            if others:
                tested += f"<div class='tiny'>on top of staged: {e(_ops_str(others))}</div>"
            if it.get("committed_ops"):
                tested += f"<div class='tiny'>and committed: {e(_ops_str(it['committed_ops']))}</div>"
            if it.get("delta") is not None:
                d, t = it["delta"], it["threshold"]
                fill_l = 50 if d >= 0 else 50 + d / scale * 50
                fill_w = abs(d) / scale * 50
                col = "var(--good)" if it["own_clears"] else ("var(--bad)" if d <= 0 else "var(--warn)")
                tick = 50 + t / scale * 50
                gauge = (f"<div class='gauge'><span class='zero'></span>"
                         f"<span class='fill' style='left:{fill_l:.1f}%;width:{fill_w:.1f}%;background:{col}'></span>"
                         f"<span class='tick' style='left:{tick:.1f}%'></span></div>"
                         f"<div class='tiny'>delta {d:+.4f} &middot; bar {t:.4f} (black tick)</div>")
            else:
                gauge = "<span class='tiny'>not evaluated</span>"
            note = f"<div class='note'>{e(it['note'])} <span class='tiny'>(LLM, numbers verified)</span></div>" if it.get("note") else ""
            out.append(f"<tr><td>{it['iteration']}</td><td>{tested}</td>"
                       f"<td class='quote'>{e(it.get('reason') or '-')}</td><td>{gauge}</td>"
                       f"<td><span class='v-{v['code']}'>{e(v['text'])}</span>{note}</td></tr>")
        out.append("</tbody></table></section>")
    tail = (f"LLM notes: {stats['verified']} verified, {len(stats.get('rejected', []))} rejected"
            if stats.get("mode") == "llm" else "LLM notes: none (template-only)")
    if stats.get("error"):
        tail += f" &middot; LLM unavailable: {e(stats['error'])}"
    out.append(f"<div class='foot'>{tail} &middot; generated {e(datetime.now().strftime('%Y-%m-%d %H:%M'))}"
               f" &middot; model {e(config.MODEL_NAME)}</div>")
    if stats.get("rejected"):
        out.append("<details><summary>Rejected LLM notes (kept out of the report above)</summary><ul class='tiny'>")
        for r in stats["rejected"]:
            out.append(f"<li>iteration {e(str(r['iteration']))}: {e('; '.join(r['why']))} &mdash; &ldquo;{e(r['note'])}&rdquo;</li>")
        out.append("</ul></details>")
    out.append("</details></main></body></html>")
    return "".join(out)


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------

def explain_run(log_path: str | Path, use_llm: bool | None = None, interpret_fn=None,
                console: bool = True, write_html: bool = True) -> dict:
    log_path = Path(log_path)
    facts = build_facts(load_run(log_path))
    if use_llm is None:
        use_llm = config.EXPLAIN_USE_LLM
    stats = {"mode": "template-only", "requested": 0, "verified": 0, "rejected": [], "error": None}
    if use_llm:
        stats = add_notes(facts, interpret_fn)
    if console:
        render_console(facts, stats)
    html_path = None
    if write_html:
        html_path = log_path.with_name(f"report_{log_path.stem}.html")
        html_path.write_text(render_html(facts, stats, log_path), encoding="utf-8")
        print(f"\nExplanation report written to: {html_path}")
    return {"facts": facts, "stats": stats, "html_path": str(html_path) if html_path else None}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Explain an AETERNA-QA audit log.")
    ap.add_argument("log", nargs="?", help="path to a run_*.json (default: newest in logs/)")
    ap.add_argument("--offline", action="store_true", help="no Groq call; verdicts only")
    ap.add_argument("--no-console", action="store_true")
    a = ap.parse_args(argv)
    path = Path(a.log) if a.log else latest_log()
    explain_run(path, use_llm=False if a.offline else None, console=not a.no_console)


if __name__ == "__main__":
    main()
