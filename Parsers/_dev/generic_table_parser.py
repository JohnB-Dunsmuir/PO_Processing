import sys, re
from pathlib import Path
import pdfplumber

# --- base_parser bootstrap ---
HERE = Path(__file__).resolve().parent
BASE = HERE / "base_parser.py"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import importlib.util
spec = importlib.util.spec_from_file_location("base_parser", BASE)
base_parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base_parser)

norm_space = base_parser.norm_space
guess_po_number = base_parser.guess_po_number
guess_po_date = base_parser.guess_po_date
guess_buyer = base_parser.guess_buyer
guess_delivery_address = base_parser.guess_delivery_address

NUM_RE = re.compile(r"[^\d\.,]")

def _clean_num(v):
    if not v:
        return ""
    v = NUM_RE.sub("", v)
    return v.replace(",", ".")

def _try_table_extract(pdf_path):
    """Try to read table grids with pdfplumber; return list of dicts."""
    items = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            try:
                tables = page.extract_tables({
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines"
                })
            except Exception:
                tables = []
            for table in tables:
                if not table or len(table) < 2:
                    continue
                header = [norm_space(h or "") for h in table[0]]
                header_line = " ".join(header).lower()
                if "qty" not in header_line or "price" not in header_line:
                    continue
                mapping = {}
                for i, h in enumerate(header):
                    hl = h.lower()
                    if "qty" in hl:
                        mapping[i] = "Quantity"
                    elif "uom" in hl or "unit" in hl or "ea" in hl:
                        mapping[i] = "UoM"
                    elif "code" in hl or "material" in hl or "part" in hl:
                        mapping[i] = "Customer Product number"
                    elif "desc" in hl:
                        mapping[i] = "Description"
                    elif "price" in hl:
                        mapping[i] = "Price/Unit"
                    elif "total" in hl or "value" in hl:
                        mapping[i] = "Line value"
                    elif "date" in hl:
                        mapping[i] = "Delivery Date"
                for row in table[1:]:
                    rec = {}
                    for idx, key in mapping.items():
                        if idx < len(row):
                            rec[key] = norm_space(row[idx] or "")
                    if rec.get("Quantity"):
                        rec["Quantity"] = _clean_num(rec["Quantity"])
                    if rec.get("Price/Unit"):
                        rec["Price/Unit"] = _clean_num(rec["Price/Unit"])
                    if rec.get("Line value"):
                        rec["Line value"] = _clean_num(rec["Line value"])
                    if rec:
                        items.append(rec)
    return items

def _fallback_text_extract(text):
    """Simple text-line parser as fallback."""
    items = []
    lines = [l for l in text.splitlines() if l.strip()]
    in_table = False
    header_map = {}
    for line in lines:
        if not in_table and re.search(r"\bqty\b", line, re.I) and re.search(r"price", line, re.I):
            in_table = True
            headers = re.split(r"\s{2,}", line.strip())
            for i, h in enumerate(headers):
                hlow = h.lower()
                if "qty" in hlow:
                    header_map[i] = "Quantity"
                elif "unit" in hlow or "ea" in hlow:
                    header_map[i] = "UoM"
                elif "code" in hlow or "material" in hlow:
                    header_map[i] = "Customer Product number"
                elif "desc" in hlow:
                    header_map[i] = "Description"
                elif "price" in hlow:
                    header_map[i] = "Price/Unit"
                elif "total" in hlow or "value" in hlow:
                    header_map[i] = "Line value"
                elif "date" in hlow:
                    header_map[i] = "Delivery Date"
            continue
        if in_table:
            if re.search(r"Goods\s+Net|VAT|Total", line, re.I):
                break
            cols = re.split(r"\s{2,}", line.strip())
            rec = {}
            for idx, key in header_map.items():
                if idx < len(cols):
                    rec[key] = norm_space(cols[idx])
            if rec:
                if "Quantity" in rec:
                    rec["Quantity"] = _clean_num(rec["Quantity"])
                if "Price/Unit" in rec:
                    rec["Price/Unit"] = _clean_num(rec["Price/Unit"])
                if "Line value" in rec:
                    rec["Line value"] = _clean_num(rec["Line value"])
                items.append(rec)
    return items

def parse(text, meta):
    """Hybrid parser: table extraction first, text fallback if none."""
    pdf_path = meta.get("file_name")
    if pdf_path and not Path(pdf_path).exists():
        root = Path(__file__).resolve().parents[1]
        candidate = root / "01_PDFs" / pdf_path
        if candidate.exists():
            pdf_path = str(candidate)
    items = []
    if pdf_path and Path(pdf_path).exists():
        items = _try_table_extract(pdf_path)
    if not items:
        items = _fallback_text_extract(text)
    header_fields = {
        "po_number": guess_po_number(text),
        "po_date": guess_po_date(text),
        "buyer": guess_buyer(text),
        "delivery_address": guess_delivery_address(text),
        "customer_name": "TLA Distribution Ltd"
        if re.search(r"\btla\s+distribution\s+ltd\b", text, re.I)
        else "",
    }
    return items, header_fields
