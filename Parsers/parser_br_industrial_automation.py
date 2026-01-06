import re

# ---------------------------------------------------------------------------
# DETECTION (STRICT VERSION)
# ---------------------------------------------------------------------------

def detect_br_industrial_automation(text: str) -> bool:
    """
    Strict detection for B&R Industrial Automation GmbH.

    Only activate when the PO clearly identifies B&R by:
    - Company name
    - Address
    - VAT
    - B&R-specific identifiers

    This prevents false positives caused by generic German terms
    like 'Bestellung', 'GmbH', 'Bestellnummer', etc.
    """
    if not text:
        return False

    t = text.upper()

    strong_triggers = [
        "B&R INDUSTRIAL AUTOMATION",
        "B & R INDUSTRIAL AUTOMATION",
        "B & R INDUSTRIE",
        "B&R STRASSE 1",
        "B&R STRAßE 1",
        "5142 EGGELSBERG",
        "EGGELSBERG",
        "ATU62367156",     # B&R VAT
        "B&R AUSTRIA",
        "BR AUTOMATION",   # sometimes appears this way
    ]

    return any(trig in t for trig in strong_triggers)


# ---------------------------------------------------------------------------
# HEADER EXTRACTION
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    m = re.search(r"Bestellnummer\/Datum\s*([0-9]+)", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"Bestellnummer\/Datum\s*[0-9]+\s*\/\s*([0-9\.]+)", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_buyer(text: str) -> str:
    m = re.search(r"AnsprechpartnerIn\/Telefon\s*([A-Za-z \.\-]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    m = re.search(
        r"Bitte liefern Sie an[: ]\s*([\s\S]*?)Liefertermin",
        text,
        flags=re.I
    )
    if m:
        block = m.group(1)
        flat = " ".join(ln.strip() for ln in block.splitlines() if ln.strip())
        return flat

    return (
        "B&R Industrial Automation GmbH, B&R Straße 1, 5142 Eggelsberg, Austria"
    )


# ---------------------------------------------------------------------------
# LINE EXTRACTION
# ---------------------------------------------------------------------------

def _to_float_eu(num: str) -> float:
    return float(num.replace(".", "").replace(",", "."))


def _extract_line(text: str) -> dict:
    header = re.search(
        r"(000\d{2})\s+([A-Za-z0-9\-]+)\s+([A-Za-z0-9\-\(\) ]+)",
        text
    )
    if not header:
        return {}

    item_no = header.group(1)
    material_code = header.group(2)
    desc = header.group(3).strip()

    num_line = re.search(
        r"([\d\.,]+)\s*St[üu]ck\s+([\d\.,]+)\/1\.000\s+([\d\.,]+)",
        text,
        flags=re.I
    )

    if num_line:
        qty_raw = num_line.group(1)
        price_raw = num_line.group(2)
        total_raw = num_line.group(3)

        quantity = qty_raw.replace(".", "").replace(",", ".")
        price = _to_float_eu(price_raw)
        total = _to_float_eu(total_raw)
    else:
        quantity = price = total = ""

    te = ""
    te_m = re.search(r"Herstellerteilenummer\s+([A-Za-z0-9\-\(\)]+)", text, flags=re.I)
    if te_m:
        te = te_m.group(1).strip()

    d_m = re.search(r"Liefertermin\s*Tag\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    delivery_date = d_m.group(1) if d_m else ""

    return {
        "item_no": item_no,
        "customer_product_no": material_code,
        "description": desc,
        "quantity": quantity,
        "uom": "Stück",
        "price": price,
        "line_value": total,
        "te_part_number": te,
        "manufacturer_part_no": te,
        "delivery_date": delivery_date,
    }


# ---------------------------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------------------------

def parse_br_industrial_automation(text: str) -> dict:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "B&R Industrial Automation GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    line = _extract_line(text)
    lines = [line] if line else []

    return {
        "header": header,
        "lines": lines,
    }
