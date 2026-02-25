import re

# Kollmorgen s.r.o. parser


def detect_kollmorgen(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    triggers = [
        "kollmorgen s.r.o.",
        "regal rexnord",
        "blanket release",
        "týn nad vltavou",
    ]
    return any(trig in t for trig in triggers)


# --------------------------------------------------
# HEADER EXTRACTION (fixed)
# --------------------------------------------------

def _extract_po_number(text: str) -> str:
    # Standalone PO like 98439-16
    m = re.search(r"\b(\d{4,}-\d+)\b", text)
    return m.group(1) if m else ""


def _extract_po_date(text: str) -> str:
    # Format like 18-AUG-2025
    m = re.search(r"\b(\d{2}-[A-Z]{3}-\d{4})\b", text)
    return m.group(1) if m else ""


def _extract_buyer(text: str) -> str:
    # Buyer appears after two dates on same line
    m = re.search(
        r"\b\d{2}-[A-Z]{3}-\d{4}\s+\d{2}-[A-Z]{3}-\d{4}\s+([A-Za-z]+\s+[A-Za-z]+)",
        text,
    )
    return m.group(1) if m else ""


def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Ship To\s*([\s\S]*?)Bill To", text, flags=re.I)
    if m:
        block = m.group(1)
        return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())
    return "Kollmorgen s.r.o., Prumyslova 1003, 375 01 Týn nad Vltavou, Czech Republic"


# --------------------------------------------------
# LINE EXTRACTION (unchanged logic)
# --------------------------------------------------

def _to_float(num: str) -> float:
    return float(num.replace(",", ""))


def _extract_lines(text: str):
    pattern = re.compile(
        r"(\d+)\s+"
        r"([A-Za-z0-9\-\/]+)\s+"
        r"([A-Za-z0-9 ,\-/]+?)\s+"
        r"([\d\.,]+)\s+([A-Za-z]+)\s+"
        r"([\d\.,]+)\s+([\d\.,]+)",
        flags=re.I,
    )

    lines = []
    for m in pattern.finditer(text):
        item_no = m.group(1)
        part = m.group(2)
        desc = m.group(3).strip()
        qty_raw = m.group(4)
        uom = m.group(5)
        price_raw = m.group(6)
        total_raw = m.group(7)

        quantity = _to_float(qty_raw)
        price = _to_float(price_raw)
        total = _to_float(total_raw)

        seg = text[m.end(): m.end() + 120]
        d_m = re.search(r"(\d{4}-\d{2}-\d{2})", seg)
        delivery_date = d_m.group(1) if d_m else ""

        lines.append({
            "item_no": item_no,
            "customer_product_no": part,
            "description": desc,
            "quantity": quantity,
            "uom": uom,
            "price": price,
            "line_value": total,
            "te_part_number": part,
            "manufacturer_part_no": part,
            "delivery_date": delivery_date,
        })

    return lines


# --------------------------------------------------
# PARSE ENTRY POINT
# --------------------------------------------------

def parse_kollmorgen(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Kollmorgen s.r.o.",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)

    return {"header": header, "lines": lines}