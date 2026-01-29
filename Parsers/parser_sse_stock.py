# Parsers/parser_sse_stock.py
import re
from typing import Dict, List, Any, Optional

def detect_sse_stock(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    # Strong SSE signals: SSE STOCK / SSE LOGISTICS / "Standard Purchase Order" + SSE
    return ("SSE STOCK" in t or "SSE LOGISTICS" in t or "SSE STOCK LTD" in t or "STANDARD PURCHASE ORDER" in t) and ("SSE" in t or "THATCHAM" in t or "THATCHAM" in t.upper())

REQUIRED_HEADER_KEYS = ["po_number", "po_date", "customer_name", "buyer", "delivery_address"]

def _nf(v: Optional[str]) -> str:
    if v is None:
        return "Not found"
    s = str(v).strip()
    return s if s else "Not found"

def _clean_ws(s: Optional[str]) -> str:
    if not s:
        return "Not found"
    return " ".join(s.split()).strip()

def _find_first(patterns, text: str, flags=0) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            if m.lastindex:
                return m.group(m.lastindex).strip()
            return m.group(0).strip()
    return None

def _norm_qty(q: str) -> str:
    if not q:
        return "Not found"
    return q.strip().replace(",", ".")

def _parse_lines(text: str) -> List[Dict[str, Any]]:
    """
    SSE pinned rule:
      - "Supplier Item" is TE part number (wins if present)
      - Stock Number remains customer_product_no
    We parse line blocks and extract Supplier Item within each block.
    """
    lines: List[Dict[str, Any]] = []
    sane_uom = {"EA","EACH","PCS","PC","SET","M","ST","STK","KIT"}

    # Work in the order lines region if possible
    start = 0
    m = re.search(r"\b(Order\s+Lines|Line\s+Items)\b", text, flags=re.IGNORECASE)
    if m:
        start = m.start()
    region = text[start:]

    # Identify each line item by "Line <n>" or a leading item number + stock number.
    # We create blocks from each detected start to the next.
    starts = []
    for mm in re.finditer(r"^\s*(?P<item>\d{1,4})\s+(?P<stock>\d{5,})\b", region, flags=re.MULTILINE):
        starts.append((mm.start(), mm.group("item"), mm.group("stock")))

    # If we can't find starts, keep previous behavior but try to at least attach Supplier Item if present.
    if not starts:
        sup = _find_first([r"\bSupplier\s+Item\s*[:\-]?\s*([A-Z0-9\-_/\.]+)\b"], region, flags=re.IGNORECASE)
        mqty = re.search(r"\b(\d{1,4}(?:[.,]\d+)?)\s+(EA|EACH|PCS|PC|STK|ST|KIT)\b", region, flags=re.IGNORECASE)
        qty = _norm_qty(mqty.group(1)) if mqty else "1"
        uom = (mqty.group(2).upper() if mqty else "EA")
        return [{
            "item_no": "1",
            "customer_product_no": "Not found",
            "te_part_number": sup if sup else "Not found",
            "manufacturer_part_no": "Not found",
            "description": "Not found",
            "quantity": qty,
            "uom": uom,
        }]

    # Build blocks
    for idx, (pos, item, stock) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(region)
        block = region[pos:end]

        te_pn = _find_first([r"\bSupplier\s+Item\s*[:\-]?\s*([A-Z0-9\-_/\.]+)\b"], block, flags=re.IGNORECASE)
        # Sometimes Supplier Item appears without colon
        if not te_pn:
            te_pn = _find_first([r"\bSupplier\s+Item\b\s+([A-Z0-9\-_/\.]+)\b"], block, flags=re.IGNORECASE)

        # Qty/UOM: take the first reasonable qty+uom after the stock number line
        mqty = re.search(r"\b(\d{1,4}(?:[.,]\d+)?)\s+(EA|EACH|PCS|PC|STK|ST|KIT)\b", block, flags=re.IGNORECASE)
        qty = _norm_qty(mqty.group(1)) if mqty else "Not found"
        uom = (mqty.group(2).upper() if mqty else "Not found")

        # Description: take a short line after stock number if available
        desc = "Not found"
        # remove first line tokens
        bl_lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if bl_lines:
            # pick the first line that is not just the header line and not "Required By:"
            for ln in bl_lines[1:6]:
                if re.search(r"^Required\s+By\s*:", ln, re.IGNORECASE):
                    continue
                if re.search(r"^Supplier\s+Item", ln, re.IGNORECASE):
                    continue
                if len(ln) > 3:
                    desc = _clean_ws(ln)
                    break

        lines.append({
            "item_no": item.strip(),
            "customer_product_no": stock.strip(),
            "te_part_number": te_pn.strip() if te_pn else "Not found",
            "manufacturer_part_no": "Not found",
            "description": desc,
            "quantity": qty,
            "uom": uom,
        })

    return lines

def parse_sse_stock(text: str) -> Dict[str, Any]:
    header = {
        "po_number": "Not found",
        "po_date": "Not found",
        "customer_name": "SSE Stock Ltd",
        "buyer": "Not found",
        "delivery_address": "Not found",
    }

    if not text:
        return {"header": header, "lines": []}

    header["po_number"] = _nf(_find_first([
        r"\bOrder\s*(?:Number|No\.?)\s*[:\-]?\s*([A-Z0-9\-\_]{4,})\b",
        r"\bOrder\s*(\d{6,})\b",
        r"\b(\d{7,})\b"
    ], text, flags=re.IGNORECASE))

    header["po_date"] = _nf(_find_first([
        r"\bOrder\s+Date\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})\b",
        r"\bOrder\s+Date\s*[:\-]?\s*(\d{2}-[A-Z]{3}-\d{4})\b",
        r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b",
        r"\b(\d{2}-[A-Z]{3}-\d{4})\b"
    ], text, flags=re.IGNORECASE))

    header["buyer"] = _nf(_find_first([
        r"\bBuyer\s*[:\-]?\s*([^\n\r]+)",
        r"\bBuyer\s*([^\n\r]+)",
        r"\bFAO\s*[:\-]?\s*([^\n\r]+)"
    ], text, flags=re.IGNORECASE))

    header["delivery_address"] = _nf(_find_first([
        r"\bDeliver(?:y|ies)?\s+To\s*[:\-]?\s*(.*?)(?:\n\s*\n|Order\b|Invoice\b|Buyer\b)",
        r"(SSE\s+LOGISTICS\s+CENTRE.*?THATCHAM.*?RG[0-9]{2})",
        r"(SSE\s+LOGISTICS.*?THATCHAM.*?UNITED KINGDOM)"
    ], text, flags=re.IGNORECASE | re.DOTALL))

    lines = _parse_lines(text)

    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": lines}
