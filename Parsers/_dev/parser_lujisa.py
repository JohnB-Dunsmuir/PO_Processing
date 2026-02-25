
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    # Remove spaces as thousand separators, then convert comma to dot
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# Lujisa S.A. (Spain) parser

def detect_lujisa(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "lujisa, s.a." in t or "suministros el\xe9ctricos" in t or "te connectivity electronics spain" in t

def _extract_po_number(text: str) -> str:
    m = re.search(r"PEDIDO\s+N\xba\s*([0-9]+)", text, flags=re.I)
    if not m:
        m = re.search(r"PEDIDO\s*\n\s*(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"FECHA DE PEDIDO\s*:\s*(\d{2} DE \w+ DE \d{4})", text, flags=re.I)
    if not m:
        return ""
    # Rough conversion: keep as-is (Spanish long form)
    return m.group(1).strip()

def _extract_buyer(text: str) -> str:
    m = re.search(r"PEDIDO POR\s*:\s*([A-ZÁÉÍÓÚÑ \.-]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    # Use TE Connectivity Electronics Spain address block
    m = re.search(r"TE CONNECTIVITY ELECTRONICS SPAIN, S\.L\.U\.\s*(.+?)\s*PEDIDO", text, flags=re.I | re.S)
    if not m:
        return "TE Connectivity Electronics Spain, S.L.U., Avda. Diagonal 123, 08005 Barcelona, Spain"
    block = m.group(1)
    return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())

def _extract_lines(text: str):
    lines = []
    # Table rows: code qty description price U.V. dto importe
    pattern = re.compile(
        r"(?P<code>\S+)\s+(?P<qty>[\d\.,]+)\s+\*?(?P<desc>.+?)\s+(?P<price>[\d\.,]+)\s+[CM]\s+\d+,\d+\s+(?P<amount>[\d\.,]+)",
        flags=re.I
    )
    idx = 10
    for m in pattern.finditer(text):
        code = m.group("code")
        qty_raw = m.group("qty")
        desc = " ".join(m.group("desc").split())
        price_raw = m.group("price")
        amount_raw = m.group("amount")

        quantity = qty_raw.replace(".", "").split(",")[0]
        price = _to_float_eu(price_raw)
        line_value = _to_float_eu(amount_raw)

        lines.append({
            "item_no": str(idx),
            "customer_product_no": code,
            "description": desc,
            "quantity": quantity,
            "uom": "PC",
            "price": price,
            "line_value": line_value,
            "te_part_number": "",
            "manufacturer_part_no": "",
            "delivery_date": "",  # separate delivery date field on doc
        })
        idx += 10

    # Delivery date is common at bottom
    return lines

def parse_lujisa(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Lujisa S.A.",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
