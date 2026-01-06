# engine/V12_enrichment.py
# ============================================================
# Enrichment + address matching (RAW vs SANITIZED)
# Keeps ALL original parsed columns; only adds new ones.
# ============================================================

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import logging
import pandas as pd
import re


# -----------------------------
# Stats
# -----------------------------
@dataclass
class AddressMatchStats:
    total_rows: int = 0
    matched_raw: int = 0
    matched_sanitized: int = 0
    unmatched: int = 0
    sanitization_changed: int = 0

    def as_dict(self) -> Dict[str, int]:
        return {
            "total_rows": int(self.total_rows),
            "matched_raw": int(self.matched_raw),
            "matched_sanitized": int(self.matched_sanitized),
            "unmatched": int(self.unmatched),
            "sanitization_changed": int(self.sanitization_changed),
        }


# -----------------------------
# Master loading
# -----------------------------
def load_master_dataframe(master_dir: Path) -> Tuple[pd.DataFrame, Path]:
    """
    Finds the master data xlsx inside 03_Master_Data.
    Prefers 'Master Data.xlsx' if present.
    """
    master_path = master_dir / "Master Data.xlsx"
    if not master_path.exists():
        # fallback: first xlsx
        candidates = sorted(master_dir.glob("*.xlsx"))
        if not candidates:
            raise FileNotFoundError(f"No master xlsx found in {master_dir}")
        master_path = candidates[-1]

    df_master = pd.read_excel(master_path)
    return df_master, master_path


# -----------------------------
# Address utilities
# -----------------------------
def _to_str(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and pd.isna(x):
        return ""
    return str(x).strip()


def sanitize_address(s: str) -> str:
    """
    Conservative sanitizer: normalize whitespace, remove obvious punctuation,
    upper-case, keep digits/letters.
    """
    s = _to_str(s)
    if not s:
        return ""
    s2 = s.upper()
    s2 = s2.replace("\n", " ")
    s2 = re.sub(r"\s+", " ", s2).strip()
    s2 = re.sub(r"[^\w\s]", " ", s2)          # drop punctuation
    s2 = re.sub(r"\s+", " ", s2).strip()
    return s2


def _build_master_address_map(df_master: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Expect master has some address-ish columns; we don’t enforce strict schema.
    We build keys from any of: 'Address', 'Ship To Address', 'Delivery Address', etc.
    The *key* is the sanitized string.
    """
    possible_cols = [
        "Address",
        "Delivery Address",
        "Ship To Address",
        "ShipToAddress",
        "Ship To",
        "Sold To Address",
        "Bill To Address",
    ]
    addr_col = next((c for c in possible_cols if c in df_master.columns), None)

    # If the master has a dedicated normalized key column, prefer it
    key_col = None
    for c in ["Address Key", "AddressKey", "SANITIZED_ADDRESS", "Sanitized Address"]:
        if c in df_master.columns:
            key_col = c
            break

    out: Dict[str, Dict[str, Any]] = {}
    for i, row in df_master.iterrows():
        raw = _to_str(row.get(addr_col, "")) if addr_col else ""
        key = _to_str(row.get(key_col, "")) if key_col else ""
        if not key:
            key = sanitize_address(raw)
        if not key:
            continue
        out[key] = {"row_index": i, "raw": raw}
    return out


def _extract_delivery_address_rowwise(df: pd.DataFrame) -> pd.Series:
    """
    Try multiple likely column names from parsers to find the delivery/ship-to address.
    Returns a Series of address strings (row-wise).
    """
    candidates = [
        "Delivery Address",
        "Ship To Address",
        "ShipToAddress",
        "Ship To",
        "Ship-To Address",
        "Deliver To",
        "Delivery",
        "Address",
    ]
    col = next((c for c in candidates if c in df.columns), None)
    if col is None:
        # no address column found => return empty series
        return pd.Series([""] * len(df), index=df.index)
    return df[col].fillna("").astype(str)


# -----------------------------
# Finalise
# -----------------------------
def finalise_parsed_dataframe(
    df_parsed: pd.DataFrame,
    df_master: pd.DataFrame,
    unmatched_xlsx: Path,
    log: Optional[logging.Logger] = None,
) -> Tuple[pd.DataFrame, AddressMatchStats]:
    """
    Adds enrichment columns WITHOUT dropping any parsed line columns.
    Writes unmatched addresses to Unmatched_Addresses.xlsx (append/merge).
    """
    if log is None:
        log = logging.getLogger("V12_ENRICHMENT")

    out = df_parsed.copy()
    stats = AddressMatchStats(total_rows=len(out))

    master_map = _build_master_address_map(df_master)

    addr_raw = _extract_delivery_address_rowwise(out)
    addr_san = addr_raw.apply(sanitize_address)

    out["Delivery Address (RAW)"] = addr_raw
    out["Delivery Address (SANITIZED)"] = addr_san
    out["Sanitization Changed"] = (addr_raw.fillna("").astype(str).str.strip() != addr_san.fillna("").astype(str).str.strip())

    # match logic
    match_status = []
    match_key = []
    match_method = []

    for raw, san in zip(addr_raw.tolist(), addr_san.tolist()):
        raw_k = sanitize_address(raw)  # normalized raw
        san_k = san

        if raw_k and raw_k in master_map:
            match_status.append("Matched")
            match_key.append(raw_k)
            match_method.append("RAW")
            stats.matched_raw += 1
        elif san_k and san_k in master_map:
            match_status.append("Matched")
            match_key.append(san_k)
            match_method.append("SANITIZED")
            stats.matched_sanitized += 1
        else:
            match_status.append("Unmatched")
            match_key.append("")
            match_method.append("")
            stats.unmatched += 1

    out["Delivery Address Match Status"] = match_status
    out["Delivery Address Match Key"] = match_key
    out["Delivery Address Match Method"] = match_method
    out["Sanitization Changed"] = out["Sanitization Changed"].astype(bool)

    stats.sanitization_changed = int(out["Sanitization Changed"].sum())

    # Write/update unmatched file
    try:
        um_rows = out.loc[out["Delivery Address Match Status"] == "Unmatched", ["Customer", "PDF Name", "Delivery Address (RAW)", "Delivery Address (SANITITZED)" if "Delivery Address (SANITITZED)" in out.columns else "Delivery Address (SANITIZED)"]].copy()
        # normalize column name
        if "Delivery Address (SANITITZED)" in um_rows.columns:
            um_rows = um_rows.rename(columns={"Delivery Address (SANITITZED)": "Delivery Address (SANITIZED)"})
        um_rows = um_rows.rename(columns={
            "Delivery Address (RAW)": "Unmatched Address (RAW)",
            "Delivery Address (SANITIZED)": "Unmatched Address (SANITIZED)",
        })

        # If there are unmatched rows, append/merge
        if not um_rows.empty:
            unmatched_xlsx.parent.mkdir(parents=True, exist_ok=True)

            if unmatched_xlsx.exists():
                existing = pd.read_excel(unmatched_xlsx)
                combined = pd.concat([existing, um_rows], ignore_index=True)
                # de-dupe
                combined = combined.drop_duplicates(subset=["Customer", "Unmatched Address (SANITIZED)"], keep="last")
            else:
                combined = um_rows

            combined.to_excel(unmatched_xlsx, index=False)
    except Exception as e:
        log.warning("Failed updating unmatched addresses file: %s", e)

    # Always return full dataset with new columns
    out = out.fillna("")
    return out, stats
