#!/usr/bin/env python3
"""Fetch the CleanML datasets used by the real-data study into Dataset/real/ (gitignored, never committed).

  python -I tools/fetch_real_data.py [--datasets Marketing Airbnb EEG] [--list]

Source: CleanML (https://github.com/chu-data-lab/CleanML), whose README points to the Dropbox archive
CleanML-datasets-2020.zip. The archive is UNTRUSTED DATA: it is downloaded into a new empty directory,
members are extracted only if their path stays inside the target (no absolute paths, no '..'), and nothing
from it is imported or executed. Prints the source URL and the sha256 of the archive and of every extracted
file. Licence notes: Airbnb is CC BY (credit Inside Airbnb; drop host name / host ID columns before use);
Marketing has no licence stated (academic use only, no redistribution, no per-ethnicity findings).
"""
import argparse
import hashlib
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "Dataset" / "real"
URL = "https://www.dropbox.com/s/nerfrhbrseev928/CleanML-datasets-2020.zip?dl=1"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", nargs="*", default=["Marketing", "Airbnb", "EEG"])
    ap.add_argument("--list", action="store_true", help="list archive members and exit")
    a = ap.parse_args(argv)
    work = Path(tempfile.mkdtemp(prefix="cleanml_dl_"))          # new, empty directory
    zp = work / "CleanML-datasets-2020.zip"
    print(f"source: {URL}")
    req = urllib.request.Request(URL, headers={"User-Agent": "aeterna-qa-fetch"})
    with urllib.request.urlopen(req) as r, open(zp, "wb") as f:
        shutil.copyfileobj(r, f)
    print(f"archive sha256: {sha256(zp)}  ({zp.stat().st_size / 1e6:.1f} MB)")
    wanted = {d.lower() for d in a.datasets}
    DEST.mkdir(parents=True, exist_ok=True)
    n = 0
    with zipfile.ZipFile(zp) as z:
        for info in z.infolist():
            parts = PurePosixPath(info.filename).parts
            if a.list:
                print("  ", info.filename, info.file_size)
                continue
            if info.is_dir() or not parts or PurePosixPath(info.filename).is_absolute() or ".." in parts:
                continue
            if not any(p.lower() in wanted for p in parts):
                continue
            if not info.filename.lower().endswith((".csv", ".txt", ".json")) or "__MACOSX" in parts:
                continue
            # keep the path below the dataset folder name, e.g. data/Marketing/raw/raw.csv -> Marketing/raw/raw.csv
            idx = next(i for i, p in enumerate(parts) if p.lower() in wanted)
            out = (DEST / Path(*parts[idx:])).resolve()
            if DEST.resolve() not in out.parents:
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
            print(f"  {out.relative_to(DEST)}  sha256 {sha256(out)}")
            n += 1
    if not a.list:
        print(f"extracted {n} file(s) to {DEST} (gitignored; never commit)")
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
