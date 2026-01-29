import re

# ---------------------------------------------------------------------------
# DETECTION (STRICT)
# ---------------------------------------------------------------------------

def detect_unionalpha(text: str) -> bool:
    if not text:
        return False

    t = text.lower()

    strong_triggers = [
        "unionalpha",
        "comunanza",
        "loc. pianerie",
        "pianerie snc",
    ]

    po_markers = ["ordine", "documento", "doc.", "rif."]

    return any(s in t for s in strong_triggers) and any(p in t for p in po_markers)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _nf(s: str) -> str:
    s = (s or "").strip()
    return s if s else "Not found"


def _fmt_date(d: str) -> str:
    if not d:
        return "Not found"
    d = d.strip()
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", d)
    if m:
        return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", d)
    if m:
        return d
    return d


def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    try:
        return float(num.replace(".", "").replace(",", "."))
    except Exception:
        return 0.0


def _all_dates(text: str):
    # collect dd/mm/yyyy and dd.mm.yyyy
    dates = set()
    for m in re.finditer(r"\b(\d{2}/\d{2}/\d{4})\b", text):
        dates.add(m.group(1))
    for m in re.finditer(r"\b(\d{2}\.\d{2}\.\d{4})\b", text):
        dates.add(m.group(1))
    # Keep stable order (appearance)
    ordered = []
    for m in re.finditer(r"\b(\d{2}[/.]\d{2}[/.]\d{4})\b", text):
        d = m.group(1)
        if d in dates and d not in ordered:
            ordered.append(d)
    return ordered


# ---------------------------------------------------------------------------
# HEADER EXTRACTION (ROBUST)
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    """
    Try multiple Italian label variants for order/document number.
    We ONLY accept a number if it's near an order-like keyword to avoid
    accidentally capturing REA / capital / VAT numbers.
    """
    patterns = [
        r"(?:ORDINE|ORD\.)\s*(?:N\.|N°|NR\.|NUMERO)?\s*[:\-]?\s*([A-Z0-9\-\/]{5,})",
        r"(?:NUMERO|NR\.)\s*(?:ORDINE|DOCUMENTO|DOC\.)\s*[:\-]?\s*([A-Z0-9\-\/]{5,})",
        r"(?:DOCUMENTO|DOC\.)\s*(?:NUMERO|NR\.)\s*[:\-]?\s*([A-Z0-9\-\/]{5,})",
        r"(?:RIF\.|RIFERIMENTO)\s*(?:N\.|N°|NR\.)\s*[:\-]?\s*([A-Z0-9\-\/]{5,})",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.I)
        if m:
            return _nf(m.group(1))

    # Fallback: look for a candidate token near keywords (within 40 chars)
    m = re.search(r"(ORDINE|DOC\.|DOCUMENTO|RIF\.|RIFERIMENTO)[^\n\r]{0,40}\b([A-Z0-9\-\/]{5,})\b", text, flags=re.I)
    if m:
        return _nf(m.group(2))

    return "Not found"


def _extract_po_date(text: str, delivery_date: str) -> str:
    """
    Prefer a date near 'Data/Del' keywords. If none, pick the first date
    that is NOT the delivery_date (if possible).
    """
    date_patterns = [
        r"(?:DATA\s+ORDINE|DATA\s+DOCUMENTO|DATA)\s*[:\-]?\s*(\d{2}[/.]\d{2}[/.]\d{4})",
        r"\bDEL\b\s*[:\-]?\s*(\d{2}[/.]\d{2}[/.]\d{4})",
        r"(?:DOC\.|DOCUMENTO)\s*DATA\s*[:\-]?\s*(\d{2}[/.]\d{2}[/.]\d{4})",
    ]
    for pat in date_patterns:
        m = re.search(pat, text, flags=re.I)
        if m:
            return _fmt_date(m.group(1).replace("/", "."))

    # Fallback: any date in the document, prefer one that isn't delivery date
    all_d = _all_dates(text)
    if all_d:
        # normalize delivery date for comparison
        dd = (delivery_date or "").replace("/", ".").strip()
        for d in all_d:
            dn = d.replace("/", ".")
            if dd and dn != dd:
                return _fmt_date(dn)
        # if only one date exists, use it
        return _fmt_date(all_d[0].replace("/", "."))

    return "Not found"


def _extract_delivery_address(text: str) -> str:
    return "UNIONALPHA SPA, 63087 Comunanza (AP) Loc. Pianerie snc, ITALY"


# ---------------------------------------------------------------------------
# LINE EXTRACTION (stable now)
# ---------------------------------------------------------------------------

def _extract_line(text: str) -> dict:
    cleaned = re.sub(r"\b(IMPORTO|DESCRIZIONE|QUANTITA|PREZZO|CONSEGNA)\b", " ", text, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned)

    line_regex = re.compile(
        r"\b(?P<ns>[A-Za-z0-9\.\-\/]{2,})\s+"
        r"(?P<te>[0-9]{1,4}-[0-9]{4,}-[0-9])\s+"
        r"(?P<te2>[0-9]{1,4}-[0-9]{4,}-[0-9])\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<uom>NR|PC|PZ|ST|MT)\s+"
        r"(?P<qty>[\d\.,]+)\s+"
        r"(?P<price>[\d\.,]+)\s+"
        r"(?P<date>\d{2}/\d{2}/\d{4}|\d{2}\.\d{2}\.\d{4})\s+"
        r"(?P<amount>[\d\.,]+)\b",
        flags=re.I
    )

    m = line_regex.search(cleaned)
    if not m:
        return {}

    ns_code = m.group("ns").strip()
    te_code = m.group("te").strip()
    desc = " ".join(m.group("desc").split()).strip()
    uom = m.group("uom").strip().upper()

    qty_raw = m.group("qty").strip()
    price_raw = m.group("price").strip()
    date_raw = m.group("date").strip().replace("/", ".")
    amount_raw = m.group("amount").strip()

    return {
        "item_no": "1",
        "customer_product_no": ns_code,
        "description": desc,
        "quantity": qty_raw,
        "uom": uom,
        "price": _to_float_eu(price_raw),
        "line_value": _to_float_eu(amount_raw),
        "te_part_number": te_code,
        "manufacturer_part_no": te_code,
        "delivery_date": _fmt_date(date_raw),
    }


# ---------------------------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------------------------

def parse_unionalpha(text: str) -> dict:
    line = _extract_line(text)
    lines = [line] if line else []

    delivery_date = ""
    if line:
        delivery_date = line.get("delivery_date", "")

    po_number = _extract_po_number(text)
    po_date = _extract_po_date(text, delivery_date)

    header = {
        "po_number": _nf(po_number),
        "po_date": _nf(po_date),
        "customer_name": "Union Alpha S.p.A.",
        "buyer": "Union Alpha S.p.A.",
        "delivery_address": _extract_delivery_address(text),
    }

    return {"header": header, "lines": lines}
