import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(".", "").replace(",", "."))

def detect_coelse(text: str) -> bool:
    t = text.lower()
    return ("comercial eléctrica de sevilla" in t
            or "coelse" in t
            or "pedido" in t and "25000210" in t)

def _extract_po_number(text: str) -> str:
    m = re.search(r"Pedido Nº:\s*(\S+)", text, flags=re.I)
    return m.group(1) if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"Fecha:\s*(\d{2}/\d{2}/\d{4})", text)
    if not m:
        return ""
    d, mo, y = m.group(1).split("/")
    return f"{d}.{mo}.{y}"

def _extract_delivery_address(text: str) -> str:
    return "Comercial Eléctrica de Sevilla, Pol. Ind. El Pino, C/ Pino Siberia 3, 41016 Sevilla, Spain"

def _extract_lines(text: str):
    lines=[]
    pat = re.compile(
        r"(?P<mat>1SNK[0-9A-Z]+R0000)\s+"
        r"(?P<desc>[^0-9]+?)\s+"
        r"(?P<qty>[\d\.,]+)\s+"
        r"(?P<price>[\d\.,]+)\s+"
        r"(?P<disc>[\d\.,]+)\s+"
        r"(?P<partial>[\d\.,]+)",
        flags=re.I
    )
    idx = 10
    for m in pat.finditer(text):
        qty = m.group("qty").replace(".", "").replace(",", "")
        price = _to_float_eu(m.group("price"))
        line_value = _to_float_eu(m.group("partial"))

        lines.append({
            "item_no": str(idx),
            "customer_product_no": m.group("mat"),
            "description": m.group("desc").strip(),
            "quantity": qty,
            "uom": "PC",
            "price": price,
            "line_value": line_value,
            "te_part_number": m.group("mat"),
            "manufacturer_part_no": "",
            "delivery_date": "",
        })
        idx += 10
    return lines

def parse_coelse(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Comercial Eléctrica de Sevilla (COELSE)",
        "buyer": "",
        "delivery_address": _extract_delivery_address(text),
    }
    return {"header": header, "lines": _extract_lines(text)}
