import re

# ---------------------------------------------------------------------------
# DETECTION
# ---------------------------------------------------------------------------

def detect_schweiger(text: str) -> bool:
    """
    Detect A. Schweiger GmbH purchase orders.
    """
    if not text:
        return False

    t = text.lower()
    triggers = [
        "schweiger gmbh",
        "bestell-nr",
        "beleg-datum",
        "lieferanten-nr",
        "artikel-nr",
        "singletec",
    ]
    return any(trig in t for trig in triggers)


# ---------------------------------------------------------------------------
# HEADER EXTRACTION
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    m = re.search(r"Bestell-Nr\.\s*:\s*([0-9]+)", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"Beleg-Datum\s*:\s*([0-9\.]+)", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_buyer(text: str) -> str:
    m = re.search(r"Sachbearbeiter\s*:\s*([A-Za-z ,\.]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    """
    No explicit delivery address → use fallback HQ.
    """
    return "A. Schweiger GmbH, Ohmstr. 1, 82054 Sauerlach, Germany"


# ---------------------------------------------------------------------------
# LINE EXTRACTION
# ---------------------------------------------------------------------------

def _to_float_eu(num: str) -> float:
    return float(num.replace(".", "").replace(",", "."))


def _extract_lines(text: str):
    """
    Multi-line Schweiger format:

    100 821.1.01.2.0016 S62A001NN00420100000 10 23,78 1 Stck 237,80
    <description lines>
    Artikel-Nr.: S62A001NN00420100000
    Liefertermin : 03.09.2025
    """

    pattern = re.compile(
        r"(\d{3,4})\s+"                 # item_no
        r"([0-9\.\-A-Za-z]+)\s+"        # customer product code
        r"([A-Za-z0-9\.\-]+)\s+"        # short description token
        r"([\d\.,]+)\s+"                # quantity
        r"([\d\.,]+)\s+"                # price
        r"[0-9]+\s+Stck\s+"             # literal "1 Stck"
        r"([\d\.,]+)",                  # line value
        flags=re.I
    )

    lines = []

    for m in pattern.finditer(text):
        item_no = m.group(1)
        cust_code = m.group(2)
        short_desc = m.group(3)
        qty_raw = m.group(4)
        price_raw = m.group(5)
        total_raw = m.group(6)

        quantity = qty_raw.replace(".", "").replace(",", ".")
        price = _to_float_eu(price_raw)
        total = _to_float_eu(total_raw)

        # Extract TE PN (Artikel-Nr.: xxxx)
        seg = text[m.end(): m.end() + 250]
        te_m = re.search(r"Artikel-Nr\.\s*:\s*([A-Za-z0-9\.\-]+)", seg, flags=re.I)
        te_part = te_m.group(1).strip() if te_m else cust_code

        # Multi-line description: take lines between short_desc and "Artikel-Nr.:"
        desc_block = ""
        desc_m = re.search(
            re.escape(short_desc) + r"(.*?)(?=Artikel-Nr\.:)",
            seg,
            flags=re.S | re.I
        )
        if desc_m:
            desc_block = " ".join(ln.strip() for ln in desc_m.group(1).splitlines() if ln.strip())

        # Delivery date
        d_m = re.search(r"Liefertermin\s*:?\s*([0-9\.]{10})", seg, flags=re.I)
        delivery_date = d_m.group(1) if d_m else ""

        description = f"{short_desc} {desc_block}".strip()

        lines.append({
            "item_no": item_no,
            "customer_product_no": cust_code,
            "description": description,
            "quantity": quantity,
            "uom": "Stck",
            "price": price,
            "line_value": total,
            "te_part_number": te_part,
            "manufacturer_part_no": te_part,
            "delivery_date": delivery_date,
        })

    return lines


# ---------------------------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------------------------

def parse_schweiger(text: str) -> dict:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "A. Schweiger GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)

    return {
        "header": header,
        "lines": lines,
    }
