
# engine/V12_parser_engine_wrappertext.py
# V12 ENGINE (WRAPPER-TEXT MODE)
#
# This version delegates PDF text extraction to diagnose_one_pdf.py
# to guarantee identical behavior to the known-good wrapper path.
#
# Drop-in replacement for engine/V12_parser_engine.py
# (you may rename this file accordingly).
#
# Parser logic, forced parser logic, and normalization remain unchanged.

from __future__ import annotations

import os
import glob
import csv
import subprocess
from pathlib import Path
from typing import Any, List, Optional, Tuple, Dict

import pandas as pd

from engine.V12_loader import load_parsers, V12ParserModule


# ------------------------------------------------------------------
# TEXT EXTRACTION (WRAPPER PATH)
# ------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Call diagnose_one_pdf.py and capture the extracted text that the
    existing wrapper/parser logic is already known to work with.
    """
    try:
        # diagnose_one_pdf.py prints extracted text between markers.
        # We capture stdout and extract the text payload.
        cmd = ["python", "diagnose_one_pdf.py", pdf_path]
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, errors="ignore")

        # Best-effort extraction of the raw text section
        # (this matches the wrapper behavior you already validated).
        marker = "=== RAW TEXT ==="
        if marker in out:
            return out.split(marker, 1)[1].strip()
        return out
    except Exception:
        return ""


# ------------------------------------------------------------------
# FORCED PARSER MAP
# ------------------------------------------------------------------

def _norm_filekey(s: str) -> str:
    return (s or "").strip().lower()


def _load_forced_parsers_map(base_dir: Path, log=None) -> Dict[str, str]:
    forced: Dict[str, str] = {}
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


def _find_parser_by_name(parser_name: str, parsers: List[V12ParserModule]) -> Optional[V12ParserModule]:
    for p in parsers:
        if getattr(p, "name", None) == parser_name:
            return p
    return None


# ------------------------------------------------------------------
# AUTO-DETECT
# ------------------------------------------------------------------

def select_parser(text: str, parsers: List[V12ParserModule]) -> Optional[Tuple[str, V12ParserModule]]:
    for p in parsers:
        try:
            if bool(p.detect(text)):
                return p.name, p
        except Exception:
            continue
    return None


# ------------------------------------------------------------------
# NORMALIZATION (UNCHANGED)
# ------------------------------------------------------------------

def _normalize_parsed_to_df(parsed: Any) -> pd.DataFrame:
    if parsed is None:
        return pd.DataFrame()

    if isinstance(parsed, pd.DataFrame):
        return parsed.copy()

    if isinstance(parsed, list):
        return pd.DataFrame(parsed) if parsed else pd.DataFrame()

    if isinstance(parsed, dict):
        if isinstance(parsed.get("lines"), list):
            header = parsed.get("header") or {}
            lines = parsed.get("lines") or []

            if not lines:
                return pd.DataFrame([header]) if header else pd.DataFrame()

            rows = []
            for ln in lines:
                row = {}
                row.update(header)
                row.update(ln)
                rows.append(row)

            return pd.DataFrame(rows)

        return pd.DataFrame([parsed])

    return pd.DataFrame()


# ------------------------------------------------------------------
# SINGLE PDF
# ------------------------------------------------------------------

def process_single_pdf(
    pdf_path: str,
    parsers: List[V12ParserModule],
    df_master: pd.DataFrame,
    log,
    forced_parser_name: Optional[str] = None,
) -> pd.DataFrame:

    text = extract_text_from_pdf(pdf_path)
    if not text.strip():
        return pd.DataFrame()

    if forced_parser_name:
        parser_obj = _find_parser_by_name(forced_parser_name, parsers)
        if not parser_obj:
            raise RuntimeError(f"Forced parser '{forced_parser_name}' not loaded")
        parser_name = forced_parser_name
    else:
        sel = select_parser(text, parsers)
        if not sel:
            return pd.DataFrame()
        parser_name, parser_obj = sel

    parsed = parser_obj.parse(text)
    df = _normalize_parsed_to_df(parsed)
    if df.empty:
        return df

    df["SourceFile"] = os.path.basename(pdf_path)
    df["ParserUsed"] = parser_name
    return df


# ------------------------------------------------------------------
# ALL PDFs
# ------------------------------------------------------------------

def process_all_pdfs(log=None) -> None:
    if log is None:
        import logging
        logging.basicConfig(level=logging.INFO)
        log = logging.getLogger("V12")

    base_dir = Path(__file__).resolve().parent.parent
    input_dir = base_dir / "01_PDFs"
    master_path = base_dir / "03_Master_Data" / "Master Data.xlsx"

    try:
        df_master = pd.read_excel(master_path, dtype=str).fillna("")
    except Exception:
        df_master = pd.DataFrame()

    parsers = load_parsers(log)
    forced_map = _load_forced_parsers_map(base_dir, log)

    pdfs = sorted(
        glob.glob(str(input_dir / "*.pdf")) + glob.glob(str(input_dir / "*.PDF"))
    )

    if forced_map:
        pdfs = [p for p in pdfs if _norm_filekey(os.path.basename(p)) in forced_map]

    frames: List[pd.DataFrame] = []

    for p in pdfs:
        forced = forced_map.get(_norm_filekey(os.path.basename(p)))
        df_one = process_single_pdf(p, parsers, df_master, log, forced)
        if not df_one.empty:
            frames.append(df_one)

    if not frames:
        return

    out = pd.concat(frames, ignore_index=True)
    out.to_excel(base_dir / "Parsed_PO_Lines.xlsx", index=False)
