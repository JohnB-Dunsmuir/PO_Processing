import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(",", ".").replace(".", "", num.count(".")-1))


def detect_sdel_controle(text: str) -> bool:
    t = text.lower()
    return ("sdel controle commande" in t
            or "ac25/02802" in t
            or "st aignan de grand lieu" in t)


def _extract_po_number(text: str) -> str:
    m = re.search(r"COMMANDE N°\s*:\s*(\S+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"le\s*(\d{2}\s+\w+\s+\d{4})", text, flags=re.I)
    if not m:
        return ""
    # Convert “20 août 2025” → dd.mm.yyyy (approx keep raw)
    return m.group(1)


def _extract_delivery_address(text: str) -> str:
    m = re.sea
