import re
# LED Controls Limited parser

def detect_led_controls(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    triggers = [
        "led controls limited",
        "led controls ltd",
        "unit 18 meadowcroft way",
        "leigh business park",
    ]
    return any(trig in t for trig in triggers)


def _extract_po_number(text: str) -> str:
    m = re.search(
        r"Purchase Order\s*(No\.?|Number)[: ]+([A-Za-z0-9\-]+)",
        text,
        flags=re.I,
    )
    return m.group(2).strip() if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"Date[: ]+(\d{2}\/\d{2}\/\d{4})", text, flags=re.I)
    if not m:
        return ""
    d = m.group(1)
    return d.replace("/", ".")


def _extract_buyer(text: str) -> str:
    m = re.search(r"Buyer[: ]+([A-Za-z ]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Deliver To\s*([\s\S]*?)Invoice To", text, flags=re.I)
    if m:
        block = m.group(1)
        return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())
    return "LED Controls Ltd, Unit 18 Meadowcroft Way, Leigh Business Park, Leigh, WN7 3XZ, UK"


def _to_float(num: str) -> float:
    return float(num.replace(",", ""))


def _extract_lines(text: str):
    pattern = re.compile(
        r"([\d\.]+)\s+([A-Za-z]+)\s+([A-Za-z0-9\-\/]+)\s+"
        r"([A-Za-z0-9 ,\-/]+?)\s+([\d\.,]+)\s+([\d\.,]+)",
        flags=re.I,
    )

    lines = []
    for idx, m in enumerate(pattern.finditer(text), start=1):
        qty_raw = m.group(1)
        uom = m.group(2)
        part = m.group(3)
        desc = m.group(4).strip()
        price_raw = m.group(5)
        total_raw = m.group(6)

        quantity = _to_float(qty_raw)
        price = _to_float(price_raw)
        total = _to_float(total_raw)

        lines.append({
            "item_no": str(idx),
            "customer_product_no": part,
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


def parse_led_controls(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "LED Controls Limited",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
