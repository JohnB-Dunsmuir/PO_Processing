# build_extractor_output.py
# STABLE – exact column names, no heuristics

from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional
import pandas as pd

REQUIRED_COLS = [
    "Purchase Order",
    "Date on PO",
    "Source.Name",
    "Quantity",
    "UoM",
    "Customer Product number",
    "Description",
    "TE Product No.",
    "Manufacturer's Part No.",
    "Delivery Date",
    "Price/Unit",
    "Unit",
    "Line value",
    "Item Number",
    "Distribution Channel",
    "Sales Org",
    "Bl",
    "Ship to ID",
    "Sold to Number",
    "Order Type",
    "Buyer",
    "Delivery Address",
    "Relevant dummy part number",
]

PARSED_MAP = {
    "Purchase Order": "po_number",
    "Date on PO": "po_date",
    "Source.Name": "SourceFile",
    "Quantity": "quantity",
    "UoM": "uom",
    "Customer Product number": "customer_product_no",
    "Description": "description",
    "TE Product No.": "te_part_number",
    "Manufacturer's Part No.": "manufacturer_part_no",
    "Delivery Date": "delivery_date",
    "Price/Unit": "price",
    "Line value": "line_value",
    "Item Number": "item_no",
    "Buyer": "buyer",
}

def col(df: pd.DataFrame, name: str) -> str:
    for c in df.columns:
        if c.strip() == name:
            return c
    raise KeyError(f"Column not found: {name}")

def build_extractor_output(
    parsed_path: Path,
    master_path: Path,
    out_xlsx: Path,
    out_csv: Optional[Path] = None,
    csv_sep: str = ";",
    unit_default: int = 1,
) -> pd.DataFrame:

    parsed_path = Path(parsed_path).resolve()
    repo_root = parsed_path.parent
    forced_csv = repo_root / "02_Parsed_Data" / "forced_parsers.csv"

    if not forced_csv.exists():
        raise FileNotFoundError(f"Missing forced_parsers.csv at {forced_csv}")

    parsed = pd.read_excel(parsed_path, dtype=str).fillna("")
    master = pd.read_excel(master_path, dtype=str).fillna("")
    forced = pd.read_csv(forced_csv, dtype=str).fillna("")

    # ---- EXACT columns ----
    sf_col = col(forced, "SourceFile")
    ship_col = col(forced, "Ship to ID")

    master_ship_col = col(master, "Ship to")
    sold_to_col = col(master, "Sold to")
    addr_col = col(master, "address_canonical")
    dist_col = col(master, "Distribution Channel")
    sales_col = col(master, "Sales Org")
    order_col = col(master, "Order Type")
    dummy_col = col(master, "Relevant dummy part number")

    source_to_ship = dict(
        zip(
            forced[sf_col].astype(str).str.strip(),
            forced[ship_col].astype(str).str.strip(),
        )
    )

    master_lookup: Dict[str, Dict[str, str]] = {}
    for _, r in master.iterrows():
        ship = str(r[master_ship_col]).strip()
        if not ship:
            continue
        master_lookup[ship] = {
            "Ship to ID": ship,
            "Sold to Number": str(r[sold_to_col]).strip(),
            "Delivery Address": str(r[addr_col]).strip(),
            "Distribution Channel": str(r[dist_col]).strip(),
            "Sales Org": str(r[sales_col]).strip(),
            "Order Type": str(r[order_col]).strip(),
            "Relevant dummy part number": str(r[dummy_col]).strip(),
            "Bl": "",
        }

    out = pd.DataFrame(index=range(len(parsed)))
    for c in REQUIRED_COLS:
        out[c] = ""

    for out_col, src_col in PARSED_MAP.items():
        if src_col in parsed.columns:
            out[out_col] = parsed[src_col].astype(str)

    out["Unit"] = unit_default

    for i, src in enumerate(parsed["SourceFile"].astype(str)):
        ship = source_to_ship.get(src.strip())
        if not ship:
            continue
        payload = master_lookup.get(ship)
        if not payload:
            continue
        for k, v in payload.items():
            out.at[i, k] = v

    for c in REQUIRED_COLS:
        out[c] = out[c].replace("", "Not found")

    out_xlsx.parent.mkdir(parents=True, exist_ok=True)
    out.to_excel(out_xlsx, index=False)

    if out_csv:
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(out_csv, sep=csv_sep, index=False)

    return out