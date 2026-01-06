import re

# ---------------------------------------------------------------------------
# DETECTION
# ---------------------------------------------------------------------------

def detect_consorzio_kct(text: str) -> bool:
    """
    Detect CONSORZIO KCT purchase orders.
    """
    if not text:
        return False

    t = text.lower()
    triggers = [
        "consorzio kct",
        "centergross",
        "numero documento",
        "data evasione",
        "iban: it92f05387",
    ]
    return any(trig in t for trig in triggers)


# ---------------------------------------------------------------------------
# HEADER EXTRACTION
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    m = re.search(r"Numero documento\s*([0-9]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"Data documento\s*([0-9]{2}\/[0-9]{2}\/[0-9]{4})", text)
    if m:
        d = m.group(1)
        return d.replace("/", ".")
    return ""


def _extract_delivery_address(text: str) -> str:
    """
    No delivery address block → use head-office fallback.
    """
    return (
        "Consorzio KCT, Via degli Orefici 169 Blocco 26, 40050 Centergross Funo di Argelato (BO), Italy"
    )


def _extract_buyer(text: str) -> str:
    # No named buyer in this PO
    return ""


# ---------------------------------------------------------------------------
# LINE EXTRACTION
# ---------------------------------------------------------------------------

def _to_float_eu(val: str) -> float:
    return float(val.replace(".", "").replace(",", "."))


def _extract_lines(text: str):
    """
    Parse rows of format:

    2116774001 GPO-135-3,2/1,6-0-SP ... MT 300,000 0,23069 69,21 27/08/2025
    """

    pattern = re.compile(
        r"([0-9]{6,})\s+"                  # Product code
        r"([A-Za-z0-9\-/., ]+?)\s+"        # Description
        r"(MT|NR)\s+"                      # UoM
        r"([\d\.,]+)\s+"                   # Quantity
        r"([\d\.,]+)\s+"                   # Price
        r"([\d\.,]+)\s+"                   # Line total
        r"(\d{2}\/\d{2}\/\d{4})",          # Delivery date
        flags=re.I
    )

    lines = []

    for m in pattern.finditer(text):
        code = m.group(1)
        desc = m.group(2).strip()
        uom = m.group(3)
        qty = m.group(4)
        price_raw = m.group(5)
        total_raw = m.group(6)
        date_raw = m.group(7)

        qty_norm = qty.replace(".", "").replace(",", ".")
        price = _to_float_eu(price_raw)
        total = _to_float_eu(total_raw)
        delivery_date = date_raw.replace("/", ".")

        # TE PN for Consorzio = first code column
        te_part = code

        lines.append({
            "item_no": "",                     # They do not provide line numbers → leave blank
            "customer_product_no": code,
            "description": desc,
            "quantity": qty_norm,
            "uom": uom,
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

def parse_consorzio_kct(text: str) -> dict:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Consorzio KCT",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)

    return {
        "header": header,
        "lines": lines,
    }
