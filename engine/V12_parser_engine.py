# engine/V12_parser_engine.py
"""
V12_parser_engine.py

Restored working contract:
- Parsers stay as-written (detect_<key>, parse_<key>) loaded by engine/V12_loader.py
- Accepted parser outputs:
  - pandas.DataFrame
  - list[dict]
  - dict
  - {"header":..., "lines":[...]}  (header stamped onto each line)
- NO forced dict/list migration outside this engine.
- Address matching optional and embedded.

ADDED (2026-01-06):
- Confidence scoring written into Parsed_PO_Lines.xlsx:
    - confidence_score (0-100)
    - confidence_level (HIGH/MEDIUM/LOW)
    - confidence_missing (missing key fields)
  Weights sum to 100 (true max = 100).

UPDATED (drop-in fix):
- Master address indexing is tolerant of the real master schema
  (delivery_address, address_key, Delivery Address Key, address_canonical, etc.)
- Address matching columns are applied to EVERY output row at end of process_all_pdfs().
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
        # Special case: {"header": {...}, "lines": [ {...}, ... ]}
        if "lines" in parsed and isinstance(parsed.get("lines"), list):
            lines = parsed.get("lines") or []
            header = parsed.get("header") or {}
            if not isinstance(header, dict):
                header = {}

            df = pd.DataFrame(lines) if lines else pd.DataFrame()
            if df.empty:
                # no lines -> still return header as single row if present
                return pd.DataFrame([header]) if header else pd.DataFrame()

            # stamp header fields onto each line (do not overwrite existing columns)
            for k, v in header.items():
                if k not in df.columns:
                    df[k] = v
            return df

        # Normal dict -> single-row
        return pd.DataFrame([parsed])

    return pd.DataFrame()


# ----------------------------
# Address matching (standing/master link) — embedded
# ----------------------------

def _sanitize_address(addr: Any) -> str:
    if not isinstance(addr, str):
        return ""
    s = addr.strip().lower()
    s = re.sub(r"[\r\n\t]+", " ", s)
    s = re.sub(r"[.,;:()\\/#\-]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _prepare_master_address_index(df_master: pd.DataFrame) -> pd.DataFrame:
    """
    Build a small index from the master table with:
      - __addr_raw__ (chosen address string)
      - __addr_san__ (sanitized for matching)
      - __site__     (site / ship-to key if present)

    Tolerant to different master schemas:
      address, delivery_address, address_key, Delivery Address Key, address_canonical, etc.

    If no usable address-like column is found, returns empty -> matching becomes no-op.
    """
    if df_master is None or df_master.empty:
        return pd.DataFrame()

    cols = {str(c).strip().lower(): c for c in df_master.columns}

    # Candidate columns for address value (priority order)
    addr_candidates = [
        "address",
        "delivery_address",
        "delivery address",
        "address_canonical",
        "address canonical",
        "delivery address key",
        "delivery_address_key",
        "address_key",
    ]

    address_col = None
    for a in addr_candidates:
        if a in cols:
            address_col = cols[a]
            break

    if address_col is None:
        return pd.DataFrame()

    # Candidate columns for site/key mapping back (priority order)
    site_candidates = [
        "delivery address key",
        "delivery_address_key",
        "address_key",
        "site",
        "site_id",
        "shipto",
        "ship_to",
    ]

    site_col = None
    for s in site_candidates:
        if s in cols:
            site_col = cols[s]
            break

    m = df_master.copy()
    m["__addr_raw__"] = m[address_col].fillna("").astype(str)
    m["__addr_san__"] = m["__addr_raw__"].map(_sanitize_address)
    m["__site__"] = m[site_col].fillna("").astype(str) if site_col else ""

    m = m[m["__addr_san__"] != ""].copy()
    return m[["__addr_raw__", "__addr_san__", "__site__"]]


def add_address_matching_columns(df: pd.DataFrame, df_master: pd.DataFrame, log) -> pd.DataFrame:
    """
    Adds, if a ship-to/delivery column exists:
      - ship_to_address_raw
      - ship_to_address_sanitized
      - ship_to_address_matched
      - ship_to_site
      - ship_to_match_method (raw|sanitized|none)
    """
    if df is None or df.empty:
        return df

    master_idx = _prepare_master_address_index(df_master)
    if master_idx.empty:
        return df

    # try common ship-to/delivery columns without forcing parser changes
    candidates = {
        "ship_to_address",
        "shipto_address",
        "ship-to address",
        "ship to address",
        "delivery_address",
        "delivery address",
        "ship_to",
        "ship to",
        "shipto",
    }

    ship_col = None
    for c in df.columns:
        cl = str(c).strip()
        if cl.lower() in candidates:
            ship_col = c
            break

    if ship_col is None:
        return df

    # Build lookup maps
    raw_map = dict(zip(master_idx["__addr_raw__"], master_idx["__site__"]))
    san_map = dict(zip(master_idx["__addr_san__"], master_idx["__site__"]))

    out = df.copy()
    out["ship_to_address_raw"] = out[ship_col].fillna("").astype(str)
    out["ship_to_address_sanitized"] = out["ship_to_address_raw"].map(_sanitize_address)

    raw_site = out["ship_to_address_raw"].map(raw_map)
    san_site = out["ship_to_address_sanitized"].map(san_map)

    out["ship_to_site"] = ""
    out["ship_to_match_method"] = "none"
    out["ship_to_address_matched"] = False

    raw_hit = raw_site.notna() & (raw_site.astype(str) != "")
    san_hit = san_site.notna() & (san_site.astype(str) != "")

    out.loc[raw_hit, "ship_to_site"] = raw_site[raw_hit].astype(str)
    out.loc[raw_hit, "ship_to_match_method"] = "raw"
    out.loc[raw_hit, "ship_to_address_matched"] = True

    out.loc[~raw_hit & san_hit, "ship_to_site"] = san_site[~raw_hit & san_hit].astype(str)
    out.loc[~raw_hit & san_hit, "ship_to_match_method"] = "sanitized"
    out.loc[~raw_hit & san_hit, "ship_to_address_matched"] = True

    if log is not None:
        log.info(
            "Address match stats: %s",
            {
                "total_rows": int(len(out)),
                "matched_raw": int(raw_hit.sum()),
                "matched_sanitized": int((~raw_hit & san_hit).sum()),
                "unmatched": int((~raw_hit & ~san_hit).sum()),
            },
        )

    return out


# ----------------------------
# Confidence scoring (0-100, weights sum to 100)
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
    if s == "":
        return False
    if s.lower() == "nan":
        return False
    return True


def _is_positive_number(x: Any) -> bool:
    try:
        if x is None:
            return False
        s = str(x).strip()
        if s == "" or s.lower() == "nan":
            return False

        # tolerate comma decimals/thousands - Excel/locales
        s = s.replace(" ", "")
        # If it has both comma and dot, assume comma is thousands (1,586.25)
        if "," in s and "." in s:
            s = s.replace(",", "")
        else:
            # If only comma, treat as decimal separator (41,73)
            if "," in s and "." not in s:
                s = s.replace(",", ".")
        v = float(s)
        return v > 0
    except Exception:
        return False


def add_confidence_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    def score_row(r) -> int:
        s = 0
        if _is_nonempty(r.get("po_number")):
            s += CONF_WEIGHTS["po_number"]
        if _is_nonempty(r.get("po_date")):
            s += CONF_WEIGHTS["po_date"]
        if _is_nonempty(r.get("customer_product_no")):
            s += CONF_WEIGHTS["customer_product_no"]
        if _is_nonempty(r.get("te_part_number")):
            s += CONF_WEIGHTS["te_part_number"]
        if _is_nonempty(r.get("manufacturer_part_no")):
            s += CONF_WEIGHTS["manufacturer_part_no"]
        if _is_positive_number(r.get("quantity")):
            s += CONF_WEIGHTS["quantity"]
        if _is_nonempty(r.get("uom")):
            s += CONF_WEIGHTS["uom"]
        if _is_positive_number(r.get("price")):
            s += CONF_WEIGHTS["price"]
        if _is_positive_number(r.get("line_value")):
            s += CONF_WEIGHTS["line_value"]
        if _is_nonempty(r.get("delivery_date")):
            s += CONF_WEIGHTS["delivery_date"]
        return int(s)

    out = df.copy()
    out["confidence_score"] = out.apply(score_row, axis=1)

    def band(v: int) -> str:
        if v >= 85:
            return "HIGH"
        if v >= 65:
            return "MEDIUM"
        return "LOW"

    out["confidence_level"] = out["confidence_score"].map(band)

    # Helpful for reporting/debugging
    key_fields = ["customer_product_no", "te_part_number", "manufacturer_part_no", "quantity", "uom", "price", "line_value"]

    def missing_list(r) -> str:
        miss = []
        for f in key_fields:
            if f in ("quantity", "price", "line_value"):
                if not _is_positive_number(r.get(f)):
                    miss.append(f)
            else:
                if not _is_nonempty(r.get(f)):
                    miss.append(f)
        return ",".join(miss)

    out["confidence_missing"] = out.apply(missing_list, axis=1)
    return out


# ----------------------------
# Main processing
# ----------------------------

def process_single_pdf(pdf_path: str, parsers: List[V12ParserModule], df_master: pd.DataFrame, log) -> pd.DataFrame:
    text = extract_text_from_pdf(pdf_path)
    if not text.strip():
        if log is not None:
            log.warning("No text extracted from %s", os.path.basename(pdf_path))
        return pd.DataFrame()

    sel = select_parser(text, parsers)
    if sel is None:
        if log is not None:
            log.warning("NO PARSER FOUND for %s", os.path.basename(pdf_path))
        return pd.DataFrame()

    parser_name, parser_obj = sel

    try:
        parsed = parser_obj.parse(text)
    except Exception as e:
        if log is not None:
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
    """
    Deterministic entry point used by V12_main.py.
    Loads master data, parses all PDFs in ./01_PDFs, writes Parsed_PO_Lines.xlsx.
    """
    if log is None:
        import logging
        logging.basicConfig(level=logging.INFO)
        log = logging.getLogger("V12")

    base_dir = Path(__file__).resolve().parent.parent
    input_dir = base_dir / "01_PDFs"

    # Master file (expected name). You already copied your clean file to this name.
    master_path = base_dir / "03_Master_Data" / "Master Data.xlsx"

    parsers = load_parsers(log)

    df_master = pd.DataFrame()
    if master_path.exists():
        try:
            df_master = pd.read_excel(master_path)
            log.info("Using Master Data: %s", str(master_path.relative_to(base_dir)))
        except Exception as e:
            log.warning("Failed to read Master Data (%s): %s", str(master_path), e)

    # Collect PDFs and de-duplicate on Windows (case-insensitive FS)
    pdfs_raw = (
        glob.glob(str(input_dir / "*.pdf")) +
        glob.glob(str(input_dir / "*.PDF"))
    )

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

    # Confidence columns
    out = add_confidence_columns(out)

    # Standing/master match columns ON EVERY OUTPUT ROW
    if not df_master.empty:
        try:
            out = add_address_matching_columns(out, df_master, log)
        except Exception as e:
            log.warning("Master enrichment failed: %s", e)

    out_path = base_dir / "Parsed_PO_Lines.xlsx"
    out.to_excel(out_path, index=False)
    log.info("Wrote output: %s (%s rows)", out_path.name, len(out))
