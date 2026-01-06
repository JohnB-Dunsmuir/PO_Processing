import re

# ---------------------------------------------------------------------------
# DETECTION
# ---------------------------------------------------------------------------

def detect_westnetz(text: str) -> bool:
    """
    Detect Westnetz GmbH purchase orders.
    """
    if not text:
        return False

    t = text.lower()
    triggers = [
        "westnetz gmbh",
        "bestellnummer",
        "lieferdatum",
        "einkaufssachbearbeiter",
        "wir sind das netz der",
    ]
    return any(trig in t for trig in triggers)


# ---------------------------------------------------------------------------
# HEADER EXTRACTION
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    m = re.search(r"Bestellnummer\s+([A-Za-z0-9\/\-]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    # Example: "29. August 2025"
    m = re.search(r"(\d{1,2}\.\s*[A-Za-z]+\s*\d{4})", text)
    return m.group(1).strip() if m else ""


def _extract_buyer(text: str) -> str:
    # Einkaufssachbearbeiter/in: Louis Postus
    m = re.search(r"Einkaufssachbearbeiter.*?:\s*([A-Za-z ]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    """
    Delivery block appears under 'Lieferadresse' until next blank line or footer.
    """
    m = re.search(r"Lieferadresse\s*([\s\S]*?)(?:\n\s*\n|$)", text, flags=re.I)
    if not m:
        return ""

    block = m.group(1)
    flat = " ".join(line.strip() for line in block.splitlines() if line.strip())
    return flat


# ---------------------------------------------------------------------------
# LINE EXTRACTION
# ---------------------------------------------------------------------------

def _to_float_de(number: str) -> float:
    """
    Converts German number format (1.530,30) → 1530.30
    """
    if not number:
        return 0.0
    cleaned = number.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except:
        return 0.0


def _extract_lines(text: str):
    """
    Westnetz lines follow this pattern:

    00010   30kV_Endmuffe      3 ST    192,49/ 1 ST    577,47
    00020   30kV_Verbindungsmuffe 3 ST 510,10/ 1 ST  1.530,30
    """

    line_regex = re.compile(
        r"(000\d{2})\s+"                  # item number, e.g. 00010
        r"([A-Za-z0-9_]+)\s+"             # material/leistung (customer product number)
        r"(\d+)\s+ST\s+"                  # quantity + ST
        r"([\d\.,]+)\s*/\s*1\s*ST\s+"     # price per unit
        r"([\d\.,]+)",                    # line total
        flags=re.I
    )

    lines = []

    for m in line_regex.finditer(text):
        item_no = m.group(1)
        customer_product = m.group(2)
        qty = m.group(3)
        price_raw = m.group(4)
        total_raw = m.group(5)

        price = _to_float_de(price_raw)
        line_value = _to_float_de(total_raw)

        lines.append({
            "item_no": item_no,
            "customer_product_no": customer_product,
            "description": customer_product,       # Same as material text
            "quantity": qty,
            "uom": "ST",
            "price": price,
            "line_value": line_value,
            "te_part_number": "",
            "manufacturer_part_no": "",
            "delivery_date": "",                  # No delivery date present
        })

    return lines


# ---------------------------------------------------------------------------
# MAIN PARSER ENTRYPOINT
# ---------------------------------------------------------------------------

def parse_westnetz(text: str) -> dict:
    """
    Return dict with "header" and "lines" for the unified engine v11.3.2.
    """

    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Westnetz GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)

    return {
        "header": header,
        "lines": lines,
    }
