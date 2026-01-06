# engine/V12_parser_engine.py
"""
V12_parser_engine.py

Restored working contract + confidence scoring (scaled to 100, NO cap).

- Parsers stay as-written (detect_<key>, parse_<key>) loaded by engine/V12_loader.py
- Accepted parser outputs:
  - pandas.DataFrame
  - list[dict]
  - dict
  - {"header":..., "lines":[...]}  (header stamped onto each line)
- NO forced dict/list migration outside this engine.
- Address matching optional and embedded (currently OFF by default).

ADDED:
- confidence_score (0-100 baseline, uncapped)
- confidence_level (HIGH/MEDIUM/LOW)
- confidence_missing
"""

from __future__ import annotations

import os
import re
import glob
from pathlib import Path
from typing import Any, List, Optional, Tuple

import pandas as pd
from pdfminer.high_level import extract_text

from engine.V12_loader import load_parsers, V12ParserModule


# ----------------------------
# Text extraction
# ----------------------------

def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        return extract_text(pdf_path) or ""
    except Exception:
        return ""


# ----------------------------
# Parser selection
# ----------------------------

def select_parser(text: str, parsers: List[V12ParserModule]) -> Optional[Tuple[str, V12ParserModule]]:
    for p in parsers:
        try:
            if bool(p.detect(text)):
                return p.name, p
        except Exception:
            continue
    return None


# ----------------------------
# Parsed output normalization
# ----------------------------

def _normalize_parsed_to_df(parsed: Any) -> pd.DataFrame:
    if parsed is None:
        return pd.DataFrame()

    if isinstance(parsed, pd.DataFrame):
        return parsed

    if isinstance(parsed, list):
        return pd.DataFrame(parsed) if parsed else pd.DataFrame()

    if isinstance(parsed, dict):
        if "lines" in parsed and isinstance(parsed.get("lines"), list):
            lines = parsed.get("lines") or []
            header = parsed.get("header") or {}
            if not isinstance(header, dict):
                header = {}

            df = pd.DataFrame(lines) if lines else pd.DataFrame()
            if df.empty:
                return pd.DataFrame([header]) if header else pd.DataFrame()

            for k, v in header.items():
                if k not in df.columns:
                    df[k] = v
            return df

        return pd.DataFrame([parsed])

    return pd.DataFrame()


# ----------------------------
# Confidence scoring (scaled to 100, uncapped)
# ----------------------------

CONF_WEIGHTS = {
    "po_number": 14,
    "po_date": 9,
    "customer_product_no": 12,
    "te_part_number": 14,
    "manufacturer_part_no": 5,
    "quantity": 12,
    "uom": 5,
    "price": 12,
    "line_value": 12,
    "delivery_date": 5,
}


def _is_nonempty(x: Any) -> bool:
    if x is None:
        return False
    s = str(x).strip()
    if s == "" or s.lower() == "nan":
        return False
    return True


def _is_positive_number(x: Any) -> bool:
    try:
        if x is None:
            return False
        s = str(x).strip()
        if s == "" or s.lower() == "nan":
            return False
        s = s.replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(",", "")
        elif "," in s:
            s = s.replace(",", ".")
        return float(s) > 0
    except Exception:
        return False


def add_confidence_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    def score_row(r) -> int:
        s = 0
        if _is_nonempty(r.get("po_number")): s += CONF_WEIGHTS["po_number"]
        if _is_nonempty(r.get("po_date")): s += CONF_WEIGHTS["po_date"]
        if _is_nonempty(r.get("customer_product_no")): s += CONF_WEIGHTS["customer_product_no"]
        if _is_nonempty(r.get("te_part_number")): s += CONF_WEIGHTS["te_part_number"]
        if _is_nonempty(r.get("manufacturer_part_no")): s += CONF_WEIGHTS["manufacturer_part_no"]
        if _is_positive_number(r.get("quantity")): s += CONF_WEIGHTS["quantity"]
        if _is_nonempty(r.get("uom")): s += CONF_WEIGHTS["uom"]
        if _is_positive_number(r.get("price")): s += CONF_WEIGHTS["price"]
        if _is_positive_number(r.get("line_value")): s += CONF_WEIGHTS["line_value"]
        if _is_nonempty(r.get("delivery_date")): s += CONF_WEIGHTS["delivery_date"]
        return int(s)

    out = df.copy()
    out["confidence_score"] = out.apply(score_row, axis=1)

    def band(v: int) -> str:
        if v >= 85: return "HIGH"
        if v >= 65: return "MEDIUM"
        return "LOW"

    out["confidence_level"] = out["confidence_score"].map(band)

    key_fields = ["customer_product_no", "te_part_number", "manufacturer_part_no", "quantity", "uom", "price", "line_value"]

    def missing_list(r) -> str:
        miss = []
        for f in key_fields:
            if f in ("quantity","price","line_value"):
                if not _is_positive_number(r.get(f)): miss.append(f)
            else:
                if not _is_nonempty(r.get(f)): miss.append(f)
        return ",".join(miss)

    out["confidence_missing"] = out.apply(missing_list, axis=1)
    return out


# ----------------------------
# Main processing
# ----------------------------

def process_single_pdf(pdf_path: str, parsers: List[V12ParserModule], df_master: pd.DataFrame, log) -> pd.DataFrame:
    text = extract_text_from_pdf(pdf_path)
    if not text.strip():
        log.warning("No text extracted from %s", os.path.basename(pdf_path))
        return pd.DataFrame()

    sel = select_parser(text, parsers)
    if sel is None:
        log.warning("NO PARSER FOUND for %s", os.path.basename(pdf_path))
        return pd.DataFrame()

    parser_name, parser_obj = sel

    try:
        parsed = parser_obj.parse(text)
    except Exception as e:
        log.error("Parse failed for %s using %s: %s", os.path.basename(pdf_path), parser_name, e)
        return pd.DataFrame()

    df = _normalize_parsed_to_df(parsed)
    if df.empty:
        return df

    if "SourceFile" not in df.columns:
        df["SourceFile"] = os.path.basename(pdf_path)
    if "ParserUsed" not in df.columns:
        df["ParserUsed"] = parser_name

    return df


def process_all_pdfs(log=None) -> None:
    if log is None:
        import logging
        logging.basicConfig(level=logging.INFO)
        log = logging.getLogger("V12")

    base_dir = Path(__file__).resolve().parent.parent
    input_dir = base_dir / "01_PDFs"
    master_path = base_dir / "03_Master_Data" / "Master Data.xlsx"

    parsers = load_parsers(log)

    df_master = pd.DataFrame()
    if master_path.exists():
        try:
            df_master = pd.read_excel(master_path)
            log.info("Using Master Data: %s", str(master_path.relative_to(base_dir)))
        except Exception as e:
            log.warning("Failed to read Master Data (%s): %s", str(master_path), e)

    pdfs_raw = glob.glob(str(input_dir / "*.pdf")) + glob.glob(str(input_dir / "*.PDF"))
    seen = set()
    pdfs: List[str] = []
    for p in pdfs_raw:
        key = os.path.abspath(p).lower()
        if key in seen:
            continue
        seen.add(key)
        pdfs.append(p)

    pdfs = sorted(pdfs)

    if not pdfs:
        log.warning("No PDFs found in %s", str(input_dir))
        return

    frames: List[pd.DataFrame] = []
    for p in pdfs:
        log.info("Processing PDF: %s", os.path.basename(p))
        df_one = process_single_pdf(p, parsers, df_master, log)
        if not df_one.empty:
            frames.append(df_one)

    if not frames:
        log.warning("No parsed rows produced.")
        return

    out = pd.concat(frames, ignore_index=True)
    out = add_confidence_columns(out)

    out_path = base_dir / "Parsed_PO_Lines.xlsx"
    out.to_excel(out_path, index=False)
    log.info("Wrote output: %s (%s rows)", out_path.name, len(out))
