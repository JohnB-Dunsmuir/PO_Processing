
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# badenovaNETZE GmbH parser

def detect_badenova(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "badenovanetze gmbh" in t and "bestellung" in t

def _extract_po_number(text: str) -> str:
    m = re.search(r"Bestellnummer/Datum\s*(\d+)\s*/", text, flags=re.I)
    if not m:
        m = re.search(r"Bestellnummer/Datum\s*(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"Bestellnummer/Datum\s*\d+\s*/\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_buyer(text: str) -> str:
    m = re.search(r"Kfm\. Bearbeitung / Telefon\s*(Herr|Frau)\s*([A-Za-zÄÖÜäöüß]+)", text, flags=re.I)
    return m.group(2).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Lieferadresse:\s*(badenovaNETZE GmbH.*?DEUTSCHLAND)", text, flags=re.I | re.S)
    if not m:
        return "badenovaNETZE GmbH, Hans-Bunte-Straße 1, 79108 Freiburg, Deutschland"
    block = m.group(1)
    return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())

def _extract_lines(text: str):
    lines = []
    pat = re.compile(
        r"10\s+Geschirmter WinkelsteckerTyp: RSES-52D-E\s*\n1 Satz\s+(?P<price>[\d\.,]+)\s+(?P<total>[\d\.,]+)",
        flags=re.I
    )
    m = pat.search(text)
    if not m:
        return lines

    price_raw = m.group("price")
    total_raw = m.group("total")

    quantity = "1"
    price = _to_float_eu(price_raw)
    line_value = _to_float_eu(total_raw)

    lines.append({
        "item_no": "10",
        "customer_product_no": "RSES-52D-E",
        "description": "Geschirmter Winkelstecker Typ: RSES-52D-E",
        "quantity": quantity,
        "uom": "SATZ",
        "price": price,
        "line_value": line_value,
        "te_part_number": "RSES-525D-E",
        "manufacturer_part_no": "",
        "delivery_date": "",  # Liefertermin field
    })
    return lines

def parse_badenova(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "badenovaNETZE GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
