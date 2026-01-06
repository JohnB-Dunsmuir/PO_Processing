import re

# -------------------------------------------------------------
# Helper
# -------------------------------------------------------------
def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    s = num.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0


# -------------------------------------------------------------
# Detect Netze BW
# -------------------------------------------------------------
def detect_netze_bw(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return (
        "NETZE BW GMBH" in t
        or "ENBW" in t
        or "4500426948" in t
        or "WARENANNAHME LOGISTIKZENTRUM STUTTGART" in t
    )


# -------------------------------------------------------------
# Header Extraction
# -------------------------------------------------------------
def _extract_po_number(text: str) -> str:
    m = re.search(r"Bestellnummer\s*(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"Datum\s*(\d{2}\.\d{2}\.\d{4})", text)
    return m.group(1) if m else ""


def _extract_buyer(text: str) -> str:
    m = re.search(r"Ansprechpartner.*?([A-Za-zÄÖÜäöüß .-]+)", text)
    if m:
        return m.group(1).strip()
    return "Netze BW Buyer"


def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Anlieferadresse:\s*(.*?)(?:Ihr Angebot|Die Rechnungsanschrift|$)",
                  text, flags=re.S | re.I)
    if m:
        block = m.group(1)
        return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())
    return "Netze BW GmbH, Warenannahme Logistikzentrum Stuttgart, Poststr. 105, 70190 Stuttgart"


# -------------------------------------------------------------
# Line extraction
# -------------------------------------------------------------
def _extract_lines(text: str):
    """
    Pattern (example from file):

    00001 000000000070003252 Verbindungsmuffe VPE 95-300 Al/Cu 20kV
    300 ST 47,15 1 ST 14.145,00
    Liefertermin 09.03.2026
    """
    lines = []

    # First capture the header line: pos, mat, desc (on its own line)
    header_pat = re.compile(
        r"\b(?P<pos>000\d+)\s+"
        r"(?P<mat>\d{12,})\s+"
        r"(?P<desc>[^\n]+)",
        flags=re.I
    )

    for h in header_pat.finditer(text):
        pos = h.group("pos")
        mat = h.group("mat")
        desc = h.group("desc").strip()

        # Look ahead after the header line for qty/price/value block
        tail = text[h.end(): h.end() + 300]
        m2 = re.search(
            r"(?P<qty>\d+)\s+ST\s+(?P<price>[\d\.,]+)\s+1\s*ST\s+(?P<total>[\d\.,]+)",
            tail, flags=re.I
        )

        if not m2:
            continue

        qty = m2.group("qty")
        price = _to_float_eu(m2.group("price"))
        total = _to_float_eu(m2.group("total"))

        # Delivery date (after qty block)
        m3 = re.search(r"Liefertermin\s*(\d{2}\.\d{2}\.\d{4})", tail)
        delivery = m3.group(1) if m3 else ""

        lines.append({
            "item_no": str(int(pos)),   # keep SAP numbering (00001 etc.)
            "customer_product_no": mat,
            "description": desc,
            "quantity": qty,
            "uom": "ST",
            "price": price,
            "line_value": total,
            "te_part_number": "",
            "manufacturer_part_no": "",
            "delivery_date": delivery,
        })

    return lines


# -------------------------------------------------------------
# Final parser
# -------------------------------------------------------------
def parse_netze_bw(text: str) -> dict:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Netze BW GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
