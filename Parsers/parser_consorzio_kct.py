import re
from typing import Dict, Any, List, Optional


# ---------------------------------------------------------------------------
# DETECTION (works for your extracted text)
# ---------------------------------------------------------------------------

def detect_consorzio_kct(text: str) -> bool:
    if not text:
        return False
    t = text.upper()

    # This doc family has a very stable TE ship-to block + Italian "Destinazione: Destinatario:"
    if ("DESTINAZIONE" in t and "DESTINATARIO" in t
        and "TE CONNECTIVITY ITALIA" in t
        and ("COLLEGNO" in t or "CORSO F.LLI CERVI" in t or "CORSO FRATELLI CERVI" in t)
        and "ORDINE" in t):
        return True

    return False


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

REQUIRED_HEADER_KEYS = ["po_number", "po_date", "customer_name", "buyer", "delivery_address"]

def _nf(v: Optional[str]) -> str:
    s = (v or "").strip()
    return s if s else "Not found"

def _clean_ws(s: Optional[str]) -> str:
    return " ".join((s or "").split()).strip()

def _fmt_date(d: str) -> str:
    # dd/mm/yyyy -> dd.mm.yyyy
    if not d:
        return "Not found"
    d = d.strip()
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", d)
    if m:
        return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
    return d

def _eu_to_float(s: str) -> float:
    if s is None:
        return 0.0
    x = str(s).strip().replace(" ", "")
    if not x:
        return 0.0
    # If comma exists => EU decimal, remove thousands dots
    if "," in x:
        x = x.replace(".", "").replace(",", ".")
    try:
        return float(x)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------

def _extract_po_date_and_number(text: str) -> (str, str):
    """
    In your extracted text we see:
      "Rif. n. fornitore Data documento Numero documento"
      "Del: / / 05/08/2025 2500507"
    """
    m = re.search(
        r"DATA\s+DOCUMENTO\s+NUMERO\s+DOCUMENTO\s+DEL:\s*/\s*/\s*(\d{2}/\d{2}/\d{4})\s+(\d{5,})",
        text,
        flags=re.IGNORECASE
    )
    if m:
        return _fmt_date(m.group(1)), m.group(2)

    # fallback (more tolerant)
    m = re.search(r"\bDEL:\s*/\s*/\s*(\d{2}/\d{2}/\d{4})\s+(\d{5,})\b", text, flags=re.IGNORECASE)
    if m:
        return _fmt_date(m.group(1)), m.group(2)

    return "Not found", "Not found"


# ---------------------------------------------------------------------------
# LINES
# ---------------------------------------------------------------------------

def _parse_lines(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []

    # Keep line breaks (this PDF extracts cleanly with \n)
    lines = (text or "").splitlines()

    # Find the header line containing "Codice" / "Descrizione" then parse from there
    start_idx = 0
    for i, ln in enumerate(lines):
        if "Codice" in ln and "Descr" in ln and "Data evasione" in ln:
            start_idx = i + 1
            break

    tail = "\n".join(lines[start_idx:]).strip()
    if not tail:
        return []

    # Flatten each physical line separately; this PDF is mostly one-row-per-line
    out: List[Dict[str, Any]] = []
    row_re = re.compile(
        # CODE
        r"^(?P<code>[A-Z0-9\-]{5,})\s+"
        # DESC (lazy)
        r"(?P<desc>.+?)\s+"
        # UOM
        r"(?P<uom>MT|NR|PC|PZ|ST)\s+"
        # QTY
        r"(?P<qty>\d[\d\.,]*)\s+"
        # PRICE
        r"(?P<price>\d[\d\.,]*)\s+"
        # AMOUNT
        r"(?P<amount>\d[\d\.,]*)\s+"
        # DELIVERY DATE
        r"(?P<date>\d{2}/\d{2}/\d{4})\s+"
        # VAT/C.I. code (e.g., 22)
        r"(?P<vat>\d{1,2})\s*$",
        flags=re.IGNORECASE
    )

    for ln in tail.splitlines():
        ln = _clean_ws(ln)
        if not ln:
            continue

        m = row_re.match(ln)
        if not m:
            continue

        code = m.group("code").strip()
        desc = _clean_ws(m.group("desc"))
        uom = m.group("uom").upper().strip()

        qty_raw = m.group("qty")
        price_raw = m.group("price")
        amount_raw = m.group("amount")
        date_raw = m.group("date")

        out.append({
            "item_no": str(len(out) + 1),
            "customer_product_no": code,
            "manufacturer_part_no": code,
            "te_part_number": code,   # enrichment mapping will resolve where needed
            "description": desc,
            "quantity": qty_raw.replace(" ", ""),
            "uom": uom,
            "price": _eu_to_float(price_raw),
            "line_value": _eu_to_float(amount_raw),
            "delivery_date": _fmt_date(date_raw),
        })

    return out


# ---------------------------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------------------------

def parse_consorzio_kct(text: str) -> Dict[str, Any]:
    po_date, po_number = _extract_po_date_and_number(text)

    header = {
        "po_number": _nf(po_number),
        "po_date": _nf(po_date),
        "customer_name": "Consorzio KCT",
        "buyer": "Consorzio KCT",  # doc doesn't reliably contain a person name
        "delivery_address": "Consorzio KCT, Via degli Orefici 169 Blocco 26, 40050 Centergross Funo di Argelato (BO), Italy",
    }

    lines = _parse_lines(text)

    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": lines}
