# Parsers/parser_kct.py
# Consorzio KCT – Italian/European Purchase Order parser
# Detects KCT POs, extracts header + lines into the unified schema:
# header:  po_number, po_date, buyer, delivery_address, customer_name
# line:    position, material_number, description, quantity, unit_price, net_value, uom (if present)

import re
import os
from datetime import datetime

DEBUG_DIR = r"C:\Users\EB005205\OneDrive - TE Connectivity\PO_Processing\02_Parsed_Data"

def _ensure_debug():
    try:
        os.makedirs(DEBUG_DIR, exist_ok=True)
    except Exception:
        pass

def _eu_to_float(s):
    if s is None:
        return 0.0
    t = str(s).strip()
    # remove thousand separators; switch decimal comma to dot
    t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except Exception:
        return 0.0

def detect_kct(text: str) -> bool:
    """
    Signals a likely Consorzio KCT PO.
    Italian headers and the supplier name are the main triggers.
    """
    t = (text or "").upper()
    return any([
        "CONSORZIO KCT" in t,
        "K.C.T" in t or "KCT " in t,
    ]) and any([
        "ORDINE" in t,               # Ordine, Ordine d'acquisto, Numero Ordine, etc.
        "DESTINAZIONE" in t,         # typical Italian header block
        "DESTINATARIO" in t,
    ])

def parse_kct(text: str) -> dict:
    """
    Robust Italian/European layout parser:
    - Flexible header matching (Numero Ordine, Data Ordine, Destinazione/Destinatario, Referente/Acquisti).
    - Line matcher tolerates columns in any of these orders:
        [pos] [desc ...] [qty] [uom?] [unit price] [line total] [material?]
      If UoM is absent, line still parses.
      If material code appears as a trailing code (e.g., '1-480763-0'), it is captured.
    """
    _ensure_debug()

    header = {"customer_name": "Consorzio KCT"}
    lines = []

    T = text or ""

    # -------------------------------
    # Header extraction
    # -------------------------------
    # Numero Ordine / Ordine n.
    m_po = re.search(r"(?:Numero\s*Ordine|Ordine\s*(?:n\.?|N\.?|No\.?)|Ordine\s*di\s*acquisto)\s*[:\-]?\s*([A-Z0-9\/\-\._]+)", T, re.IGNORECASE)
    header["po_number"] = (m_po.group(1).strip() if m_po else "")

    # Data Ordine dd/mm/yyyy or dd.mm.yyyy
    m_date = re.search(r"(?:Data\s*Ordine|Data)\s*[:\-]?\s*(\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{2,4})", T, re.IGNORECASE)
    po_date = ""
    if m_date:
        raw = m_date.group(1).replace("-", "/").replace(".", "/")
        try:
            d, m, y = [int(x) for x in raw.split("/")]
            if y < 100: y += 2000
            po_date = datetime(y, m, d).strftime("%Y-%m-%d")
        except Exception:
            po_date = ""
    header["po_date"] = po_date

    # Buyer / Referente / Ufficio Acquisti (best effort)
    m_buyer = re.search(r"(?:Referente|Ufficio\s*Acquisti|Contatto|Resp\.\s*Acquisti)\s*[:\-]\s*([^\n\r]+)", T, re.IGNORECASE)
    header["buyer"] = (m_buyer.group(1).strip() if m_buyer else "")

    # Delivery address from Destinazione: (stop at Destinatario: or a large gap)
    m_dest = re.search(r"Destinazione\s*:\s*([\s\S]{0,300}?)(?:\n{2,}|Destinatario\s*:|Fornitore\s*:|Cliente\s*:)", T, re.IGNORECASE)
    delivery_address = ""
    if m_dest:
        delivery_address = " ".join(m_dest.group(1).split())
    else:
        # Sometimes the label order is reversed; also try Destinatario:
        m_dest2 = re.search(r"Destinatario\s*:\s*([\s\S]{0,300}?)(?:\n{2,}|Destinazione\s*:|Fornitore\s*:|Cliente\s*:)", T, re.IGNORECASE)
        if m_dest2:
            delivery_address = " ".join(m_dest2.group(1).split())
    header["delivery_address"] = delivery_address

    # -------------------------------
    # Line extraction
    # -------------------------------
    # We accept line shapes like (any order of numbers, with EU-style separators):
    #   [POS]  <DESCRIPTION ...>  QTY  [UOM?]  PRICE  TOTAL  [MATERIAL?]
    #
    # Where:
    #   POS        = 1..6 digits
    #   QTY        = 1.000,000 or 100,00 etc.
    #   PRICE      = 0,13174 etc.
    #   TOTAL      = 395,22 etc.
    #   MATERIAL   = trailing code like 1-480763-0 (alnum/.-)
    #
    # We'll look for a "numeric cluster" near each candidate line and capture description between the position and numbers.
    eu_num      = r"\d{1,3}(?:\.\d{3})*(?:,\d+)?"
    code_token  = r"[A-Za-z0-9][A-Za-z0-9\.\-_/]{3,}"  # material/TE codes
    uom_token   = r"(?:PZ|NR|PCS|PCE|PEZZI|UN|EA|ST|KIT|SET|CF|RL|ROTOLO|BOB|MT|M|KG|L)\b"

    line_rx = re.compile(
        rf"""
        (?P<pos>\b\d{{1,6}}\b)                              # position (optional but typical)
        [^\n\r]{{0,80}}?                                    # small gap
        (?P<desc>[^\n\r]{{5,200}}?)                         # description (greedy but capped)
        \s+(?P<qty>{eu_num})                                # quantity (EU format)
        (?:\s+(?P<uom>{uom_token}))?                        # optional UoM
        \s+(?P<price>{eu_num})                              # unit price
        \s+(?P<total>{eu_num})                              # line total
        (?:\s+(?P<mat>{code_token}))?                       # optional trailing material code
        """,
        re.IGNORECASE | re.VERBOSE
    )

    matches_dbg = []
    for m in line_rx.finditer(T):
        pos   = m.group("pos")
        desc  = (m.group("desc") or "").strip(" -;:\t")
        qty   = _eu_to_float(m.group("qty"))
        price = _eu_to_float(m.group("price"))
        total = _eu_to_float(m.group("total"))
        uom   = (m.group("uom") or "").upper()
        mat   = (m.group("mat") or "")

        # If we didn't catch a material code, try to pull a code-like token from the tail of the description
        if not mat:
            tail_codes = re.findall(code_token, desc)
            if tail_codes:
                mat = tail_codes[-1]  # last code-looking token

        # Clean description (remove trailing code if duplicated)
        if mat and desc.endswith(mat):
            desc = desc[: -len(mat)].strip(" -;:")

        item = {
            "position": pos.zfill(5),
            "material_number": mat,
            "description": desc,
            "quantity": qty,
            "uom": uom,
            "unit_price": price,
            "net_value": total,
        }
        lines.append(item)
        matches_dbg.append(f"POS {item['position']} | QTY={qty} {uom} | PRICE={price} | TOTAL={total} | MAT={mat} | DESC={desc[:80]}")

    # Dump debug
    try:
        with open(os.path.join(DEBUG_DIR, "debug_kct_matches.txt"), "w", encoding="utf-8") as f:
            if matches_dbg:
                f.write("\n".join(matches_dbg))
            else:
                f.write("No line matches found. Please share this file so we can adjust the regex window.")
    except Exception:
        pass

    return {"header": header, "lines": lines}


def detect_consorzio_kct(text: str) -> bool:
    # Detects Consorzio Kct purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "CONSORZIO KCT" in t,                 # company name
        "@CONSORZIOKCT.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
