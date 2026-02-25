import re

# ---------------------------------------------------------------------------
# DETECTION
# ---------------------------------------------------------------------------

def detect_bayernwerk(text: str) -> bool:
    """
    Detect Bayernwerk Netz GmbH purchase orders.
    """
    if not text:
        return False

    t = text.lower()
    triggers = [
        "bayernwerk netz gmbh",
        "bestellnummer",
        "materialwirtschaft",
        "eggenfelden",
        "dieter kellner",
    ]
    return any(trig in t for trig in triggers)


# ---------------------------------------------------------------------------
# HEADER EXTRACTION
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    m = re.search(r"Bestellnummer\s*([0-9\/]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    # e.g. 19. August 2025
    m = re.search(r"(\d{1,2}\.\s*[A-Za-zäöüÄÖÜ]+\.?\s*\d{4})", text)
    return m.group(1).strip() if m else ""


def _extract_buyer(text: str) -> str:
    m = re.search(r"Einkaufssachbearbeiter\/in:\s*([A-Za-z ,\.]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    """
    Extract Lieferadresse block; if missing, fallback to HQ.
    """
    m = re.search(
        r"Lieferadresse\s*([\s\S]*?)Zahlungsbedingungen",
        text,
        flags=re.I
    )
    if m:
        block = m.group(1)
        flat = " ".join(ln.strip() for ln in block.splitlines() if ln.strip())
        return flat

    return "Bayernwerk Netz GmbH, Lilienthalstraße 7, 93049 Regensburg, Germany"


# ---------------------------------------------------------------------------
# LINE EXTRACTION
# ---------------------------------------------------------------------------

def _to_float_eu(num: str) -> float:
    return float(num.replace(".", "").replace(",", "."))


def _extract_line(text: str) -> dict:
    """
    Format:

    00010 9314890729 Doppelgewindebolzen...
    20 SAT 25,25/ 1 SAT 505,00
    SAP-Nr. CU2787-005
    Liefertermin: 11.09.2025
    """

    # Identify the line header
    hdr = re.search(
        r"(000\d{2})\s+([0-9]+)\s+([A-Za-z0-9 ,;\-\/\.]+)",
        text
    )
    if not hdr:
        return {}

    item_no = hdr.group(1)
    material = hdr.group(2)
    short_desc = hdr.group(3).strip()

    # Quantity, unit, price, total
    num = re.search(
        r"([\d]+)\s+([A-Za-z]+)\s+([\d\.,]+)\s*\/\s*1\s*[A-Za-z]+\s+([\d\.,]+)",
        text,
        flags=re.I
    )

    if num:
        qty = num.group(1)
        uom = num.group(2)
        price = _to_float_eu(num.group(3))
        total = _to_float_eu(num.group(4))
    else:
        qty = uom = ""
        price = total = ""

    # TE PN via SAP-Nr.
    te = ""
    te_m = re.search(r"SAP-Nr\.\s*([A-Za-z0-9\-]+)", text, flags=re.I)
    if te_m:
        te = te_m.group(1).strip()

    # Delivery date
    d_m = re.search(r"Liefertermin\s*:\s*([0-9\.]{10})", text, flags=re.I)
    delivery_date = d_m.group(1) if d_m else ""

    # Capture full description block
    # from immediately after short_desc until SAP-Nr.
    desc = ""
    block_m = re.search(
        re.escape(short_desc) + r"(.*?)(?=SAP-Nr|\Z)",
        text,
        flags=re.S | re.I
    )
    if block_m:
        desc = " ".join(ln.strip() for ln in block_m.group(1).splitlines() if ln.strip())

    description = f"{short_desc} {desc}".strip()

    return {
        "item_no": item_no,
        "customer_product_no": material,
        "description": description,
        "quantity": qty,
        "uom": uom,
        "price": price,
        "line_value": total,
        "te_part_number": te,
        "manufacturer_part_no": te,
        "delivery_date": delivery_date,
    }


# ---------------------------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------------------------

def parse_bayernwerk(text: str) -> dict:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Bayernwerk Netz GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    line = _extract_line(text)
    lines = [line] if line else []

    return {
        "header": header,
        "lines": lines,
    }
