import re
# Neways Electronics Riesa GmbH parser

def detect_neways_riesa(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    triggers = [
        "neways electronics riesa",
        "riesa gmbh",
        "auftragsbestätigung",
        "neways electronics international",
    ]
    return any(trig in t for trig in triggers)


def _extract_po_number(text: str) -> str:
    m = re.search(r"Auftragsbest.?tigung\s*Nr\.?:\s*([A-Za-z0-9\-\/]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"Datum\s*:\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_buyer(text: str) -> str:
    m = re.search(r"Ansprechpartner\s*:\s*([A-Za-zÄÖÜäöüß \-]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Lieferadresse\s*([\s\S]*?)Rechnungsadresse", text, flags=re.I)
    if m:
        block = m.group(1)
        return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())
    return "Neways Electronics Riesa GmbH, Paul-Greifzu-Straße 37, 01591 Riesa, Germany"


def _to_float_eu(num: str) -> float:
    return float(num.replace(".", "").replace(",", "."))


def _extract_lines(text: str):
    pattern = re.compile(
        r"(\d{3})\s+"
        r"([A-Za-z0-9\.\-]+)\s+"
        r"([\d\.,]+)\s+"
        r"([A-Za-z]+)\s+"
        r"([\d\.,]+)\s+"
        r"([\d\.,]+)\s+"
        r"(\d{2}\.\d{2}\.\d{4})",
        flags=re.I,
    )

    lines = []
    for m in pattern.finditer(text):
        item_no = m.group(1)
        material = m.group(2)
        qty_raw = m.group(3)
        uom = m.group(4)
        price_raw = m.group(5)
        total_raw = m.group(6)
        delivery_date = m.group(7)

        quantity = qty_raw.replace(".", "").replace(",", ".")
        price = _to_float_eu(price_raw)
        total = _to_float_eu(total_raw)

        seg = text[m.end(): m.end() + 200]
        desc = ""
        for ln in seg.splitlines():
            ls = ln.strip()
            if ls:
                desc = ls
                break

        lines.append({
            "item_no": item_no,
            "customer_product_no": material,
            "description": desc,
            "quantity": quantity,
            "uom": uom,
            "price": price,
            "line_value": total,
            "te_part_number": "",
            "manufacturer_part_no": "",
            "delivery_date": delivery_date,
        })

    return lines


def parse_neways_riesa(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Neways Electronics Riesa GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
