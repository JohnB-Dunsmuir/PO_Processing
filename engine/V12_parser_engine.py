# engine/V12_parser_engine.py
# RESTORED NON-DEBUG ENGINE
# Rebuilds Parsed_PO_Lines.xlsx from wrapper results

from __future__ import annotations

import os
import glob
import csv
from pathlib import Path
import pandas as pd

from diagnose_one_pdf import diagnose_one_pdf_wrapper


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


def process_all_pdfs(log=None) -> None:
    base_dir = Path(__file__).resolve().parent.parent
    input_dir = base_dir / "01_PDFs"
    out_xlsx = base_dir / "Parsed_PO_Lines.xlsx"

    forced_map = _load_forced_parsers_map(base_dir)

    pdfs = sorted(
        glob.glob(str(input_dir / "*.pdf")) +
        glob.glob(str(input_dir / "*.PDF"))
    )

    if forced_map:
        pdfs = [
            p for p in pdfs
            if _norm_filekey(os.path.basename(p)) in forced_map
        ]

    rows = []

    for pdf in pdfs:
        fname = os.path.basename(pdf)
        forced_parser = forced_map.get(_norm_filekey(fname))

        result = diagnose_one_pdf_wrapper(
            pdf_path=pdf,
            forced_parser=forced_parser,
            stdout=True,
        )

        header = result.get("header", {})
        lines = result.get("lines", [])
        parser_used = result.get("detected_parser")

        for line in lines:
            row = {
                "SourceFile": fname,
                "ParserUsed": parser_used,
                **header,
                **line,
            }
            rows.append(row)

    # Rebuild from scratch
    df = pd.DataFrame(rows)
    df.to_excel(out_xlsx, index=False)

    return