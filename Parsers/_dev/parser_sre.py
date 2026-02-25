
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    # Remove spaces as thousand separators, then convert comma to dot
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# SRE (Synergie Réseaux Électricité) parser

def detect_sre(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "synergie r\xe9seaux \xe9lectricit" in t or "sre/f" in t or "commande" in t and "michaud logistique" in t

def _extract_po_number(text: str) -> str:
    m = re.search(r"Commande\s*(SRE/\w+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"Commande\s*SRE/\w+\s*(\d{2}/\d{2}/\d{4})", text, flags=re.I)
    if not m:
        m = re.search(r"(\d{2}/\d{2}/\d{4})", text)
    return m.group(1).replace("/", ".") if m else ""

def _extract_buyer(text: str) -> str:
    m = re.search(r"Acheteur\s*\n?([A-Za-z \-]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Adresse de livraison\s*(.*?)\s*Adresse du fournisseur", text, flags=re.I | re.S)
    if not m:
        return ""
    block = m.group(1)
    return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())

def _extract_lines(text: str):
    lines = []
    # Each line has pattern: [code] description ... internal ref qty U date price amount
    pattern = re.compile(
        r"\[(?P<code>[^\]]+)\]\s+(?P<desc>.+?)\s+TYC?[A-Z0-9\-]+\s+"
        r"(?P<qty>[\d\., ]+)\s+U\s+(?P<date>\d{2}/\d{2}/\d{4})\s+"
        r"(?P<price>[\d\., ]+)\s+(?P<amount>[\d\., ]+)\s+€",
        flags=re.I | re.S
    )
    idx = 10
    for m in pattern.finditer(text):
        code = m.group("code").strip()
        desc_raw = m.group("desc")
        # Take first line of desc_raw
        desc = " ".join(desc_raw.split()).strip()
        qty_raw = m.group("qty").strip()
        date_raw = m.group("date").strip()
        price_raw = m.group("price").strip()
        amount_raw = m.group("amount").strip()

        quantity = qty_raw.replace(" ", "").replace(".", "").split(",")[0]
        delivery_date = date_raw.replace("/", ".")
        price = _to_float_eu(price_raw)
        line_value = _to_float_eu(amount_raw)

        lines.append({
            "item_no": str(idx),
            "customer_product_no": code,
            "description": desc,
            "quantity": quantity,
            "uom": "U",
            "price": price,
            "line_value": line_value,
            "te_part_number": "",
            "manufacturer_part_no": "",
            "delivery_date": delivery_date,
        })
        idx += 10

    return lines

def parse_sre(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "SRE",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
