
# engine/V12_parser_engine.py
# TEMPORARY DEBUG VERSION
#
# PURPOSE:
# - Run diagnose_one_pdf.py as a subprocess
# - PRINT RAW WRAPPER OUTPUT VERBATIM
# - Do NOT attempt to parse it
#
# Use this ONCE to capture the wrapper's real stdout format.
# Then discard this file.

from __future__ import annotations

import os
import glob
import csv
import subprocess
from pathlib import Path


def _norm_filekey(s: str) -> str:
    return (s or "").strip().lower()


def _load_forced_parsers_map(base_dir: Path):
    forced = {}
    csv_path = base_dir / "02_Parsed_Data" / "forced_parsers.csv"
    if not csv_path.exists():
        return forced

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            src = _norm_filekey(row.get("SourceFile") or "")
            key = (row.get("forced_parser") or "").strip()
            if src and key:
                forced[src] = key
    return forced


def _run_wrapper(pdf_path: str) -> str:
    cmd = ["python", "diagnose_one_pdf.py", pdf_path]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="ignore",
        check=False,
    )
    return proc.stdout or ""


def process_all_pdfs(log=None) -> None:
    base_dir = Path(__file__).resolve().parent.parent
    input_dir = base_dir / "01_PDFs"

    forced_map = _load_forced_parsers_map(base_dir)

    pdfs = sorted(
        glob.glob(str(input_dir / "*.pdf")) + glob.glob(str(input_dir / "*.PDF"))
    )

    if forced_map:
        pdfs = [p for p in pdfs if _norm_filekey(os.path.basename(p)) in forced_map]

    for p in pdfs:
        print("\n===== WRAPPER RAW OUTPUT FOR:", os.path.basename(p), "=====")
        out = _run_wrapper(p)
        print(out)
        print("===== END WRAPPER OUTPUT =====\n")

    # Intentionally do NOT create Parsed_PO_Lines.xlsx
    return
