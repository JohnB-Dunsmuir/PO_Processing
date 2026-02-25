print("NEW BR PARSER ACTIVE")
import re
from typing import Dict, List, Any, Optional


def detect_br_industrial_automation(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return "B&R INDUSTRIAL AUTOMATION" in t or "EGGELSBERG" in t or "B&R STRASSE" in t


REQUIRED_HEADER_KEYS = ["po_number", "po_date", "customer_name", "buyer", "delivery_address"]


def _nf(v: Optional[str]) -> str:
    if v is None:
        return "Not found"
    s = str(v).strip()
    return s if s else "Not found"


def _clean_ws(s: Optional[str]) -> str:
    if not s:
        return "Not found"
    return " ".join(str(s).split()).strip()


def _find_first(patterns, text: str, flags=0) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            if m.lastindex:
                return m.group(m.lastindex).strip()
            return m.group(0).strip()
    return None


def _norm_qty(x: str) -> str:
    if not x:
        return "Not found"
    s = x.strip().replace(" ", "")
    if re.match(r"^\d{1,3}(?:\.\d{3})+(?:,\d+)?$", s):
        s = s.replace(".", "").replace(",", ".")
        return s
    return s.replace(",", ".")


# ---------------------------------------------------
# ITEM BLOCK ISOLATION
# ---------------------------------------------------

def _isolate_item_block(text: str) -> str:
    start = re.search(r"Pos\.\s+Material", text, flags=re.IGNORECASE)
    if not start:
        return text

    block = text[start.end():]

    end = re.search(
        r"(Herstellerteilenummer|Ihre Materialnummer|Seite\s*/|\bPage\b)",
        block,
        flags=re.IGNORECASE,
    )
    if end:
        block = block[:end.start()]

    return block


# ---------------------------------------------------
# VARIANT B – INLINE LAYOUT
# ---------------------------------------------------

def _extract_variant_b(text: str) -> List[Dict[str, Any]]:
    rows = []
    block = _isolate_item_block(text)

    lines = [l.strip() for l in block.splitlines() if l.strip()]

    buffer = ""

    for line in lines:

        if re.match(r"^\d{5}\s+[A-Z0-9\.\-]+", line):
            if buffer:
                parsed = _parse_inline_row(buffer)
                if parsed:
                    rows.append(parsed)
            buffer = line
        else:
            buffer += " " + line

        if "Stück" in buffer:
            parsed = _parse_inline_row(buffer)
            if parsed:
                rows.append(parsed)
            buffer = ""

    if buffer:
        parsed = _parse_inline_row(buffer)
        if parsed:
            rows.append(parsed)

    return rows


def _parse_inline_row(line: str) -> Optional[Dict[str, Any]]:
    tokens = line.split()

    try:
        item_no = tokens[0]
        material = tokens[1]

        uom_idx = next(i for i, t in enumerate(tokens) if t.lower() == "stück")

        qty = _norm_qty(tokens[uom_idx - 1])
        description = " ".join(tokens[2:uom_idx - 1])

        return {
            "item_no": item_no,
            "te_part_number": material,
            "description": description if description else material,
            "quantity": qty,
            "uom": "ST",
        }

    except Exception:
        return None# ---------------------------------------------------
# ORIGINAL VARIANT A – TWO-LINE LAYOUT (UNCHANGED)
# ---------------------------------------------------

def _extract_variant_a(text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    pat = re.compile(
        r"^\s*(?P<item>\d{5})\s+(?P<mat>[A-Z0-9\-]+)\s+(?P<tail>.+?)\s*$"
        r"(?:\r?\n|\r)\s*(?P<qty>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s+Stück\b",
        re.IGNORECASE | re.MULTILINE,
    )

    for m in pat.finditer(text):
        item = m.group("item").strip()
        mat = m.group("mat").strip()
        tail = _clean_ws(m.group("tail"))
        qty = _norm_qty(m.group("qty"))

        te = _find_first(
            [r"\b\d-\d{6,}-\d\b", r"\b[0-9]{1}-[0-9]{3,}-[0-9]\b", r"\b[0-9\-]{6,}\b"],
            tail,
            flags=re.IGNORECASE,
        )

        te_part = te if te else mat

        rows.append({
            "item_no": item,
            "te_part_number": te_part,
            "description": tail if tail != "Not found" else te_part,
            "quantity": qty,
            "uom": "ST",
        })

    return rows


# ---------------------------------------------------
# MASTER LINE PARSER
# ---------------------------------------------------

def _parse_lines(text: str) -> List[Dict[str, Any]]:

    # Try Variant B first
    rows_b = _extract_variant_b(text)
    if rows_b:
        return rows_b

    # Fallback to Variant A
    rows_a = _extract_variant_a(text)
    if rows_a:
        return rows_a

    # Final fallback TE detection
    te2 = _find_first(
        [r"\b\d-\d{6,}-\d\b", r"\b[0-9]{3,}-[0-9]{1,}\b"],
        text,
        flags=re.IGNORECASE,
    )

    if te2:
        return [{
            "item_no": "1",
            "te_part_number": te2,
            "description": te2,
            "quantity": "1",
            "uom": "EA",
        }]

    return [{
        "item_no": "1",
        "te_part_number": "Not found",
        "description": "Not found",
        "quantity": "1",
        "uom": "EA",
    }]


# ---------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------

def parse_br_industrial_automation(text: str) -> Dict[str, Any]:
    header = {
        "po_number": "Not found",
        "po_date": "Not found",
        "customer_name": "B&R Industrial Automation GmbH",
        "buyer": "Not found",
        "delivery_address": "Not found",
    }

    if not text:
        return {"header": header, "lines": []}

    po_m = re.search(
        r"Bestellnummer/Datum\s*([0-9]+)\s*/\s*(\d{2}\.\d{2}\.\d{4})",
        text,
        flags=re.IGNORECASE,
    )

    if po_m:
        header["po_number"] = _nf(po_m.group(1))
        header["po_date"] = _nf(po_m.group(2))
    else:
        header["po_number"] = _nf(_find_first([r"\b(45\d{8,})\b"], text, flags=re.IGNORECASE))
        header["po_date"] = _nf(_find_first([r"\b(\d{2}\.\d{2}\.\d{4})\b"], text, flags=re.IGNORECASE))

    header["buyer"] = _nf(_find_first([r"AnsprechpartnerIn/Telefon\s*([^\n\r]+)"], text, flags=re.IGNORECASE))

    addr = _find_first(
        [r"(B&R Industrial Automation GmbH.*?ÖSTERREICH)",
         r"(B&R Industrial Automation GmbH.*?Eggelsberg)"],
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    header["delivery_address"] = _nf(addr)

    lines = _parse_lines(text)

    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": lines}