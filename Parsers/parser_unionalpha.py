import re

# ---------------------------------------------------------------------------
# DETECTION
# ---------------------------------------------------------------------------

def detect_unionalpha(text: str) -> bool:
    """
    Detect Union Alpha S.p.A. purchase orders.
    """
    if not text:
        return False

    t = text.lower()
    triggers = [
        "unionalpha spa",
        "unionalpha s.p.a",
        "ordine acquisto",
        "documento numero",
        "partita iva",
    ]
    return any(trig in t for trig in triggers)


# ---------------------------------------------------------------------------
# HEADER EXTRACTION
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    # DOCUMENTO NUMERO 25001350
    m = re.search(r"DOCUMENTO\s+NUMERO\s+(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    # DOCUMENTO DATA 14/07/2025
    m = re.search(r"DOCUMENTO\s+DATA\s+(\d{2}\/\d{2}\/\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    """
    Union Alpha POs do not include a separate ship-to address.
    Per your rule: use the head office address from the header/footer.
    """
    # Try to pick up the 'Sede Legale e Stabilimento' block if present.
    m = re.search(
        r"Sede Legale e Stabilimento:\s*([^\n\r]+)",
        text,
        flags=re.I
    )
    if m:
        addr_core = m.group(1).strip()
    else:
        # Fallback: generic head office string
        addr_core = "63087 Comunanza (AP) Loc. Pianerie snc"

    # Final canonical address
    return f"UNIONALPHA SPA, {addr_core}, ITALY"


# ---------------------------------------------------------------------------
# LINE EXTRACTION
# ---------------------------------------------------------------------------

def _to_float_eu(num: str) -> float:
    """
    Convert European number: 3.008,54 → 3008.54
    """
    if not num:
        return 0.0
    cleaned = num.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except:
        return 0.0


def _extract_line(text: str) -> dict:
    """
    Extracts the single line item from Union Alpha's PO format.

    Example:
    CON11VICSE.M2  3-1534799-1  3-1534799-1  CON 11V 6C R2.5 MK2 SELE  NR  29.568  0,1018  15/07/2025  3.008,54
    """

    line_regex = re.compile(
        r"([A-Za-z0-9\.\-]+)\s+"           # NS.CODICE
        r"([A-Za-z0-9\.\-]+)\s+"           # VS.CODICE (TE PN)
        r"([A-Za-z0-9\.\-]+)\s+"           # repeated TE PN
        r"([A-Za-z0-9 ,\.\-/]+?)\s+"       # DESCRIZIONE
        r"([A-Za-z]{1,3})\s+"              # U.M. (NR)
        r"([\d\.,]+)\s+"                   # QUANTITA'
        r"([\d\.,]+)\s+"                   # PREZZO UNIT.
        r"(\d{2}\/\d{2}\/\d{4})\s+"        # CONSEGNA
        r"([\d\.,]+)",                     # IMPORTO
        flags=re.I
    )

    m = line_regex.search(text)
    if not m:
        return {}

    ns_codice = m.group(1)
    te_code = m.group(2)
    description = " ".join(m.group(4).split())
    uom = m.group(5)
    qty_raw = m.group(6)
    price_raw = m.group(7)
    delivery_date = m.group(8)
    total_raw = m.group(9)

    price = _to_float_eu(price_raw)
    line_value = _to_float_eu(total_raw)

    # Quantity: keep as string but normalised (29.568 → 29.568)
    qty = qty_raw.replace(" ", "")

    return {
        "item_no": "1",
        "customer_product_no": ns_codice,
        "description": description,
        "quantity": qty,
        "uom": uom,
        "price": price,
        "line_value": line_value,
        "te_part_number": te_code,
        "manufacturer_part_no": te_code,
        "delivery_date": delivery_date,
    }


# ---------------------------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------------------------

def parse_unionalpha(text: str) -> dict:
    """
    Returns the header + lines dict expected by v11.3.2 unified engine.
    """

    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Union Alpha S.p.A.",
        "buyer": "",
        "delivery_address": _extract_delivery_address(text),
    }

    line = _extract_line(text)
    lines = [line] if line else []

    return {
        "header": header,
        "lines": lines,
    }
