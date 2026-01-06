import re

# ---------------------------------------------------------------------------
# DETECTION
# ---------------------------------------------------------------------------

def detect_pronet(text: str) -> bool:
    """
    Detect Pronet GmbH purchase orders.
    """
    if not text:
        return False

    t = text.lower()
    triggers = [
        "pronet gmbh",
        "bestellung",
        "b307",          # Pronet PO prefixes
        "artikelnummer",
        "stk.",
    ]
    return any(trig in t for trig in triggers)


# ---------------------------------------------------------------------------
# HEADER EXTRACTION
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    # Example: Bestellung B307389
    m = re.search(r"Bestellung\s+([A-Za-z0-9]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    # Datum: 26.08.2025
    m = re.search(r"Datum[: ]+(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_buyer(text: str) -> str:
    # Ihr/e Ansprechpartner/in Maschka Graf
    m = re.search(r"Ansprechpartner/in\s+([A-Za-zÄÖÜäöüß ]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    """
    No delivery address shown → use global head-office fallback.
    """
    return (
        "PRONET GmbH, Otto-Hahn-Str. 2a, 63110 Rodgau, Germany"
    )


# ---------------------------------------------------------------------------
# LINE EXTRACTION
# ---------------------------------------------------------------------------

def _to_float_eu(num: str) -> float:
    return float(num.replace(".", "").replace(",", "."))


def _extract_lines(text: str):
    """
    Line format:

    1.  400 Stk. 50.041.00
    Ihre Nummer: 50-0041-000-100
    <description>
    KW 35/2025
    0,65   260,00
    """

    lines = []

    header_regex = re.compile(
        r"(\d+)\.\s+"                # line number
        r"(\d+)\s+Stk\.\s+"          # quantity
        r"([A-Za-z0-9\.\-]+)",       # customer material
        flags=re.I
    )

    for m in header_regex.finditer(text):
        item_no = m.group(1)
        qty = m.group(2)
        cust_mat = m.group(3)

        # Find TE PN (Ihre Nummer: XXXXX)
        start = m.end()
        segment = text[start:start+300]
        te_m = re.search(r"Ihre Nummer[: ]+([A-Za-z0-9\.\-]+)", segment, flags=re.I)
        te_part = te_m.group(1).strip() if te_m else cust_mat

        # Find description (lines between material header and price row)
        desc_m = re.search(
            r"Ihre Nummer.*?\n([\s\S]*?)(?=KW|\d+,\d+\s+\d+,\d+|$)",
            segment,
            flags=re.I
        )
        if desc_m:
            desc_block = " ".join(
                ln.strip() for ln in desc_m.group(1).splitlines() if ln.strip()
            )
        else:
            desc_block = ""

        # Price row: E-Preis (€)   G-Preis (€)
        # Example: "0,65 260,00"
        price_m = re.search(
            r"(\d+,\d+)\s+(\d+,\d+)",
            segment,
            flags=re.I
        )
        if price_m:
            price = _to_float_eu(price_m.group(1))
            line_value = _to_float_eu(price_m.group(2))
        else:
            price = ""
            line_value = ""

        lines.append({
            "item_no": item_no,
            "customer_product_no": cust_mat,
            "description": desc_block,
            "quantity": qty,
            "uom": "STK",
            "price": price,
            "line_value": line_value,
            "te_part_number": te_part,
            "manufacturer_part_no": te_part,
            "delivery_date": "",   # only KW shown → leave blank
        })

    return lines


# ---------------------------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------------------------

def parse_pronet(text: str) -> dict:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Pronet GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)

    return {
        "header": header,
        "lines": lines,
    }
