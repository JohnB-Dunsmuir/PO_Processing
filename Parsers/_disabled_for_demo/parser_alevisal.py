import re
# Almacenes Eléctricos Vitoria S.L. (AleviSal) parser

def detect_alevisal(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    triggers = [
        "almacenes eléctricos vitoria",
        "alevisal",
        "vitoria-gasteiz",
        "alavesa de electricidad",
    ]
    return any(trig in t for trig in triggers)


def _extract_po_number(text: str) -> str:
    m = re.search(r"Pedido\s*n[ºo]\s*[:\-]?\s*([A-Za-z0-9\-]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"Fecha\s*[:\-]?\s*(\d{2}\/\d{2}\/\d{4})", text, flags=re.I)
    if not m:
        return ""
    d = m.group(1)
    return d.replace("/", ".")


def _extract_buyer(text: str) -> str:
    m = re.search(
        r"Persona de contacto\s*[:\-]?\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+)",
        text,
        flags=re.I,
    )
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Direcci.n de entrega\s*([\s\S]*?)Forma de pago", text, flags=re.I)
    if m:
        block = m.group(1)
        return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())
    return "Almacenes Eléctricos Vitoria S.L., C/ Portal de Gamarra 18, 01013 Vitoria-Gasteiz, Spain"


def _to_float_eu(num: str) -> float:
    return float(num.replace(".", "").replace(",", "."))


def _extract_lines(text: str):
    pattern = re.compile(
        r"([A-Za-z0-9\-]+)\s+"
        r"([A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ ,\.\-]+?)\s+"
        r"([\d\.,]+)\s+"
        r"([A-Za-z]+)\s+"
        r"([\d\.,]+)\s+"
        r"([\d\.,]+)",
        flags=re.I,
    )

    lines = []
    for idx, m in enumerate(pattern.finditer(text), start=1):
        code = m.group(1)
        desc = m.group(2).strip()
        qty_raw = m.group(3)
        uom = m.group(4)
        price_raw = m.group(5)
        total_raw = m.group(6)

        quantity = qty_raw.replace(".", "").replace(",", ".")
        price = _to_float_eu(price_raw)
        total = _to_float_eu(total_raw)

        lines.append({
            "item_no": str(idx),
            "customer_product_no": code,
            "description": desc,
            "quantity": quantity,
            "uom": uom,
            "price": price,
            "line_value": total,
            "te_part_number": "",
            "manufacturer_part_no": "",
            "delivery_date": "",
        })

    return lines


def parse_alevisal(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Almacenes Eléctricos Vitoria S.L.",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
