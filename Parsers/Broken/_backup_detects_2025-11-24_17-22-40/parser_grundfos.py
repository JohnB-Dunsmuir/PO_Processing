# Parsers/parser_grundfos.py
# Grundfos Operations – bilingual (EN + DA/NO) European PO parser
# Output schema:
#   header: po_number, po_date, buyer, delivery_address, customer_name
#   lines:  position, material_number, description, quantity, unit_price, net_value, uom (optional)

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
    # Handle 1.234,56 → 1234.56 and 1,234.56 → 1234.56
    # First try EU style
    t_eu = t.replace(".", "").replace(",", ".")
    try:
        return float(t_eu)
    except Exception:
        pass
    # Fallback: US style
    t_us = t.replace(",", "")
    try:
        return float(t_us)
    except Exception:
        return 0.0

def detect_grundfos(text: str) -> bool:
    """
    Detects Grundfos Operations purchase orders.
    Triggers on 'GRUNDFOS' plus a PO cue in EN/DA/NO.
    """
    t = (text or "").upper()
    has_brand = ("GRUNDFOS" in t)
    has_po_cue = any(k in t for k in [
        "PURCHASE ORDER", "ORDER NUMBER", "ORDER NO", "PO NUMBER",
        "ORDRENUMMER", "ORDRE NR", "ORDRENr", "BESTILLING", "INNKJØP", "INNKJOEP", "KJØP", "KJOEP"
    ])
    return has_brand and has_po_cue

def parse_grundfos(text: str) -> dict:
    """
    Parses European/Scandinavian layout with bilingual labels.
    Attempts to extract:
      - PO number: 'Order Number'/'Order No'/'Ordrenummer'/'Ordre nr'
      - Date: 'Date'/'Dato'
      - Buyer/contact: 'Buyer'/'Contact'/'Attn'/'Bestiller'
      - Delivery address: 'Deliver To'/'Delivery Address'/'Ship To'/'Leveringsadresse'
      - Lines with: position, material, description, qty (Mængde/Mengde/Quantity), UoM (optional),
                    unit price (Enhedspris), line total (Beløb/Amount)
    """
    _ensure_debug()
    header = {"customer_name": "Grundfos Operations"}
    lines = []
    T = text or ""

    # -------------------------------
    # Header extraction
    # -------------------------------
    # PO number (English & Scandinavian)
    m_po = re.search(
        r"(?:Purchase\s*Order|Order\s*(?:No\.?|Number|#)|Ordre(?:\s*nr\.?|nummer)|Ordrenummer)\s*[:\-]?\s*([A-Z0-9\-/\.]+)",
        T, re.IGNORECASE
    )
    header["po_number"] = (m_po.group(1).strip() if m_po else "")

    # Date / Dato (DD/MM/YYYY, DD.MM.YYYY, YYYY-MM-DD)
    m_date = re.search(
        r"(?:Order\s*Date|Date|Dato)\s*[:\-]?\s*(\d{1,4}[\/\.\-]\d{1,2}[\/\.\-]\d{1,4})",
        T, re.IGNORECASE
    )
    po_date = ""
    if m_date:
        raw = m_date.group(1)
        # Normalize separators to '/'
        norm = raw.replace("-", "/").replace(".", "/")
        parts = norm.split("/")
        try:
            if len(parts[0]) == 4:
                # YYYY/MM/DD
                y, m, d = [int(x) for x in parts]
            else:
                # DD/MM/YYYY
                d, m, y = [int(x) for x in parts]
                if y < 100:
                    y += 2000
            po_date = datetime(y, m, d).strftime("%Y-%m-%d")
        except Exception:
            po_date = ""
    header["po_date"] = po_date

    # Buyer / Contact / Bestiller / Attn
    m_buyer = re.search(
        r"(?:Buyer|Contact|Requested\s*By|Attn|Attention|Bestiller|Indk(?:ø|oe)ber)\s*[:\-]\s*([^\n\r]+)",
        T, re.IGNORECASE
    )
    header["buyer"] = (m_buyer.group(1).strip() if m_buyer else "")

    # Delivery address: Deliver To / Delivery Address / Ship To / Leveringsadresse
    m_del = re.search(
        r"(?:Deliver\s*To|Delivery\s*Address|Ship\s*To|Leveringsadresse)\s*[:\-]?\s*([\s\S]{0,300}?)(?:\n{2,}|Invoice|Faktura|Terms|Item|Linje|Line|Pos)",
        T, re.IGNORECASE
    )
    delivery_address = ""
    if m_del:
        delivery_address = " ".join(m_del.group(1).split())
    header["delivery_address"] = delivery_address

    # -------------------------------
    # Line extraction
    # -------------------------------
    # Common bilingual labels:
    #   Quantity / Qty / Mængde / Mengde
    #   Unit Price / Enhedspris / Enhetspris
    #   Amount / Total / Beløb / Belop / Beløp
    #
    # Layouts to support:
    #   POS  CODE  DESCRIPTION ...  QTY  [UOM]  UNIT_PRICE  LINE_TOTAL
    #   POS  DESCRIPTION ... QTY [UOM] UNIT_PRICE LINE_TOTAL CODE
    uom_token = r"(?:EA|PCS|PCE|PC|PACK|BOX|SET|KIT|RL|ROLL|M|MT|KG|L|ST|STK|STK\.|PK|SÆT|SAET|ENH|ENHED|UNIT|EACH)\b"
    code_token = r"[A-Za-z0-9][A-Za-z0-9\.\-_/]{3,}"
    # numeric with EU/US tolerance
    num_token = r"(?:\d{1,3}(?:[.,]\d{3})*[.,]\d+|\d+(?:[.,]\d+)?)"

    primary_rx = re.compile(
        rf"""
        (?P<pos>\b\d{{1,6}}\b)                # position
        \s+
        (?P<mat>{code_token})                 # material code
        \s+
        (?P<desc>[^\n\r]{{5,220}}?)           # description
        \s+
        (?P<qty>{num_token})                  # quantity
        (?:\s+(?P<uom>{uom_token}))?          # optional UoM
        \s+
        (?P<price>{num_token})                # unit price
        \s+
        (?P<total>{num_token})                # line total
        """,
        re.IGNORECASE | re.VERBOSE
    )

    fallback_rx = re.compile(
        rf"""
        (?P<pos>\b\d{{1,6}}\b)
        \s+
        (?P<desc>[^\n\r]{{6,240}}?)
        \s+
        (?P<qty>{num_token})
        (?:\s+(?P<uom>{uom_token}))?
        \s+
        (?P<price>{num_token})
        \s+
        (?P<total>{num_token})
        (?:\s+(?P<mat>{code_token}))?
        """,
        re.IGNORECASE | re.VERBOSE
    )

    matches_dbg, used_spans = [], []

    def _span_free(m):
        a, b = m.span()
        for x, y in used_spans:
            if not (b <= x or a >= y):
                return False
        return True

    for m in primary_rx.finditer(T):
        if not _span_free(m):
            continue
        pos   = m.group("pos")
        mat   = (m.group("mat") or "").strip()
        desc  = (m.group("desc") or "").strip(" -;:\t")
        qty   = _eu_to_float(m.group("qty"))
        uom   = (m.group("uom") or "").upper()
        price = _eu_to_float(m.group("price"))
        total = _eu_to_float(m.group("total"))

        lines.append({
            "position": pos.zfill(5),
            "material_number": mat,
            "description": desc,
            "quantity": qty,
            "uom": uom,
            "unit_price": price,
            "net_value": total,
        })
        used_spans.append(m.span())
        matches_dbg.append(f"ROW {pos} | MAT={mat} | QTY={qty} {uom} | PRICE={price} | TOTAL={total} | DESC={desc[:80]}")

    for m in fallback_rx.finditer(T):
        if not _span_free(m):
            continue
        pos   = m.group("pos")
        desc  = (m.group("desc") or "").strip(" -;:\t")
        qty   = _eu_to_float(m.group("qty"))
        uom   = (m.group("uom") or "").upper()
        price = _eu_to_float(m.group("price"))
        total = _eu_to_float(m.group("total"))
        mat   = (m.group("mat") or "")

        if not mat:
            tail = re.findall(code_token, desc)
            if tail:
                mat = tail[-1]
        if mat and desc.endswith(mat):
            desc = desc[: -len(mat)].strip(" -;:")

        lines.append({
            "position": pos.zfill(5),
            "material_number": mat,
            "description": desc,
            "quantity": qty,
            "uom": uom,
            "unit_price": price,
            "net_value": total,
        })
        used_spans.append(m.span())
        matches_dbg.append(f"FB  {pos} | MAT={mat} | QTY={qty} {uom} | PRICE={price} | TOTAL={total} | DESC={desc[:80]}")

    # Dump debug for fast tuning
    try:
        with open(os.path.join(DEBUG_DIR, "debug_grundfos_matches.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(matches_dbg) if matches_dbg else "No Grundfos line matches found.")
    except Exception:
        pass

    return {"header": header, "lines": lines}


def detect_grundfos(text: str) -> bool:
    # Detects Grundfos purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "GRUNDFOS" in t,                 # company name
        "@GRUNDFOS.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
