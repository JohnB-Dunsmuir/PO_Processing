import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# Detect A.E.E. / COOP SOA orders
def detect_aee_soa(text: str) -> bool:
    t = text.lower()
    return ("coop soa" in t or "a.e.e" in t or "ordini di acquisto" in t)

def _extract_po_number(text: str) -> str:
    m = re.search(r"Ordine Acquisto.*?(\d{2}-\d{5})", text, flags=re.I)
    if not m:
        m = re.search(r"25-00\d{3}", text)
    return m.group(1) if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"Data d[’']ordine.*?(\d{2}\.\d{2}\.\d{4})", text)
    return m.group(1) if m else ""

def _extract_delivery_address(text: str) -> str:
    # Use “Spett.le” block
    m = re.search(r"Spett\.?(.*?)Cod\.fornitore", text, flags=re.S | re.I)
    if not m:
        return "TE Connectivity Italia Distribution SRL, Corso Fratelli Cervi, 10093 Collegno (TO)"
    block = m.group(1)
    return " ".join(i.strip() for i in block.splitlines() if i.strip())

def _extract_lines(text: str):
    lines = []

    # Extract line blocks — Italian-style rotated PDF
    pat = re.compile(
        r"(?P<mat>EN\d+)\s+"
        r"(?P<desc>CONN.*?|CONF.*?|LV26.*?|AMP.*?).*?"
        r"(?P<qty>\d+)\s+NR.*?"
        r"(?P<price>[\d\.,]+)",
        flags=re.S | re.I
    )

    idx = 10
    for m in pat.finditer(text):
        mat = m.group("mat").strip()
        desc = " ".join(m.group("desc").split())
        qty = m.group("qty")
        price = _to_float_eu(m.group("price"))
        line_value = price * int(qty)

        lines.append({
            "item_no": str(idx),
            "customer_product_no": mat,
            "description": desc,
            "quantity": qty,
            "uom": "NR",
            "price": price,
            "line_value": line_value,
            "te_part_number": "",
            "manufacturer_part_no": "",
            "delivery_date": "",
        })
        idx += 10

    return lines

def parse_aee_soa(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "AEE / COOP SOA",
        "buyer": "",
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
