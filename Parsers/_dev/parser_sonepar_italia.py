import re

# ---------------------------------------------------------------------------
# DETECTION
# ---------------------------------------------------------------------------

def detect_sonepar(text: str) -> bool:
    """
    Detect Sonepar Italia purchase orders.
    """
    if not text:
        return False

    t = text.lower()
    triggers = [
        "sonepar italia",
        "ordine d'acquisto",
        "cod. fornitore",
        "p.i./c.f. it00825330285",
    ]
    return any(trig in t for trig in triggers)


# ---------------------------------------------------------------------------
# HEADER EXTRACTION
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    m = re.search(r"Ordine d['’]Acquisto N[°º]\s*:\s*(\d+)", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"del\s*:\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_delivery_address(text: str) -> str:
    """
    Delivery block starts after "Spedire a:".
    Fallback: main Sonepar HQ address.
    """
    m = re.search(
        r"Spedire a[: ]\s*([\s\S]*?)N\.B\.",
        text,
        flags=re.I
    )
    if m:
        block = m.group(1)
        flat = " ".join(line.strip() for line in block.splitlines() if line.strip())
        return flat

    # fallback
    return (
        "Sonepar Italia S.p.A., Via Riviera Maestri del Lavoro 24, 35127 Padova (PD), Italy"
    )


# ---------------------------------------------------------------------------
# LINE EXTRACTION
# ---------------------------------------------------------------------------

def _to_float_eu(num: str) -> float:
    """
    Convert EU format 7,32 → 7.32
    """
    return float(num.replace(".", "").replace(",", "."))


def _extract_lines(text: str):
    """
    Italian line structure:

    10 Vs. cod. art.: TYC1SET411012R0000 28 PZ 26.09.2025 7,32 x 1
    CANALINA DI CABLAGGIO PVC 40X100 GRIGIA
    """

    # Match the compact numeric line:
    compact = re.compile(
        r"(\d{2})\s+Vs\.?\s*cod\.?\s*art\.?\s*[: ]\s*([A-Za-z0-9\-]+)\s+"
        r"(\d+)\s+PZ\s+"
        r"(\d{2}\.\d{2}\.\d{4})\s+"
        r"([\d\.,]+)",
        flags=re.I
    )

    lines = []

    for m in compact.finditer(text):
        item_no = m.group(1)
        code = m.group(2)
        qty = m.group(3)
        delivery_date = m.group(4)
        price_raw = m.group(5)

        price = _to_float_eu(price_raw)

        # Extract description = the line after numeric block
        # Grab ~200 chars after match and take the first non-empty text line
        after = text[m.end(): m.end() + 200]
        desc_line = ""
        for line in after.splitlines():
            ls = line.strip()
            if ls:
                desc_line = ls
                break

        description = desc_line

        lines.append({
            "item_no": item_no,
            "customer_product_no": code,
            "description": description,
            "quantity": qty,
            "uom": "PZ",
            "price": price,
            "line_value": "",            # Sonepar does NOT provide line totals
            "te_part_number": code,
            "manufacturer_part_no": code,
            "delivery_date": delivery_date,
        })

    return lines


# ---------------------------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------------------------

def parse_sonepar(text: str) -> dict:
    """
    Return v11.3.2-compliant {header, lines}.
    """

    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Sonepar Italia S.p.A.",
        "buyer": "",
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)

    return {
        "header": header,
        "lines": lines,
    }
