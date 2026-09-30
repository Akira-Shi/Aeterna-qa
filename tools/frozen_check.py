#!/usr/bin/env python3
"""Frozen-file integrity check for AETERNA-QA (stdlib only).

  python tools/frozen_check.py --init    # baseline from git HEAD blobs (not the working tree)
  python tools/frozen_check.py           # compare working tree to baseline

Exit codes: 0 clean | 1 FROZEN mismatch (halt, ask Akira) | 2 WATCHED mismatch
(gate/commit-rule-adjacent; needs Akira's OK) | 3 setup problem.
Hashes are line-ending independent (CRLF -> LF), so Windows checkouts compare equal.
PREREGISTRATION.md: sections 1-11 and 13+ must be byte-identical; section 12 is
append-only, so every baseline amendment row must still be present unchanged.
"""
import hashlib, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tools" / "frozen_manifest.json"
FROZEN = ["aeterna_qa/modules/evaluator.py", "aeterna_qa/modules/evaluator_tests.py"]
WATCHED = ["aeterna_qa/modules/config.py", "aeterna_qa/modules/study.py", "aeterna_qa/modules/injection.py"]
PREREG = "Documents/PREREGISTRATION.md"


def norm(b: bytes) -> str:
    return b.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def read_wt(rel):
    return norm((ROOT / rel).read_bytes())


def read_head(rel):
    out = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT, capture_output=True)
    if out.returncode != 0:
        sys.exit(f"cannot read {rel} from git HEAD: {out.stderr.decode().strip()}")
    return norm(out.stdout)


def split_prereg(text):
    i, j = text.find("\n## 12."), text.find("\n## 13.")
    if i < 0 or j < 0 or j < i:
        sys.exit("PREREGISTRATION.md: cannot locate section 12 / 13 headings")
    outside = text[:i] + "\n@@S12@@\n" + text[j:]
    s12 = text[i:j]
    rows = [l.strip() for l in s12.splitlines() if l.startswith("| 20")]
    return outside, rows


def snapshot(reader):
    snap = {"frozen": {p: h(reader(p)) for p in FROZEN},
            "watched": {p: h(reader(p)) for p in WATCHED}}
    outside, rows = split_prereg(reader(PREREG))
    snap["prereg_outside_s12"] = h(outside)
    snap["prereg_s12_rows"] = [h(r) for r in rows]
    return snap


def main():
    if "--init" in sys.argv:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        snap = snapshot(read_head)
        snap["baseline_commit"] = head
        MANIFEST.write_text(json.dumps(snap, indent=2) + "\n")
        print(f"baseline written from git HEAD {head}: {len(FROZEN)} frozen, {len(WATCHED)} watched, "
              f"{len(snap['prereg_s12_rows'])} amendment rows")
        return 0
    if not MANIFEST.exists():
        print("no manifest; run --init first"); return 3
    base = json.loads(MANIFEST.read_text())
    cur = snapshot(read_wt)
    frozen_bad, watched_bad = [], []
    for p, hh in base["frozen"].items():
        if cur["frozen"].get(p) != hh: frozen_bad.append(p)
    if cur["prereg_outside_s12"] != base["prereg_outside_s12"]:
        frozen_bad.append(f"{PREREG} (sections other than 12)")
    missing = [i + 1 for i, r in enumerate(base["prereg_s12_rows"]) if r not in cur["prereg_s12_rows"]]
    if missing:
        frozen_bad.append(f"{PREREG} section 12: baseline amendment row(s) {missing} edited or removed (append-only)")
    for p, hh in base["watched"].items():
        if cur["watched"].get(p) != hh: watched_bad.append(p)
    added = len(cur["prereg_s12_rows"]) - len(base["prereg_s12_rows"])
    if added > 0:
        print(f"note: {added} amendment row(s) appended to section 12 since baseline (allowed; Akira must have signed them)")
    if frozen_bad:
        print("FROZEN MISMATCH -> HALT and ask Akira:"); [print("  -", x) for x in frozen_bad]; return 1
    if watched_bad:
        print("WATCHED file changed -> needs Akira's OK before commit:"); [print("  -", x) for x in watched_bad]; return 2
    print(f"clean (baseline {base.get('baseline_commit','?')})"); return 0


if __name__ == "__main__":
    sys.exit(main())
