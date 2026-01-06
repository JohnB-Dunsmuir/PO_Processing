
import re

def _to_float_eu(num: str) -> float:
    return float(num.replace(".", "").replace(",", ".")) if num else 0.0

# Sigmatek GmbH & Co KG parser

def detect_sigmatek(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "sigmatek gmbh & co kg" in t or "sigmatekstraße" in t or "sigmatek.at" in t

def _extract_po_number(text: str) -> str:
    m = re.search(r"Belegnummer\s*(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"Belegdatum\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_buyer(text: str) -> str:
    m = re.search(r"Einkäufer\s*([A-Za-zÄÖÜäöüß ]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Lieferanschrift\s*(.*?)\s*Zahlungsbedingungen", text, flags=re.I | re.S)
    if not m:
        return "Sigmatek GmbH & Co KG, Bahnhofstraße 2, 5112 Lamprechtshausen, Österreich"
    block = m.group(1)
    return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())

def _extract_lines(text: str):
    lines = []

    # Material number (customer)
    m_mat = re.search(r"\b(\d{10})\b", text)
    customer_mat = m_mat.group(1) if m_mat else ""

    # Quantity and UOM
    m_qty = re.search(r"(\d{1,3}[\.\d]*,\d{2})\s*(ST|Stück|STK)", text, flags=re.I)
    qty_raw = m_qty.group(1) if m_qty else ""
    uom = m_qty.group(2).upper() if m_qty else ""

    # Price per 1000 (we'll convert to per unit)
    m_price = re.search(r"ST\s+([\d\.,]+)\s*EUR/1\.000", text, flags=re.I)
    price_per_1000_raw = m_price.group(1) if m_price else ""

    # Total line/net value (single-line order → equals line value)
    m_total = re.search(r"Gesamtnettowert ohne Mwst\s*([\d\.,]+)", text, flags=re.I)
    total_raw = m_total.group(1) if m_total else ""

    # Description – text between price block and 'Ihre Materialnummer'
    m_desc = re.search(r"EUR/1\.000\s*(.*?)Ihre Materialnummer", text, flags=re.S | re.I)
    desc = ""
    if m_desc:
        # take first non-empty line
        for ln in m_desc.group(1).splitlines():
            ln = ln.strip()
            if ln:
                desc = ln
                break

    # TE part from 'Ihre Materialnummer'
    m_te = re.search(r"Ihre Materialnummer[: ]+([A-Za-z0-9\-\/]+)", text, flags=re.I)
    te_part = m_te.group(1).strip() if m_te else ""

    # Delivery date
    m_del = re.search(r"Lieferdatum[: ]+(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    delivery_date = m_del.group(1).strip() if m_del else ""

    # Normalise numbers
    quantity = ""
    if qty_raw:
        # convert "1.120,00" -> "1120"
        q = qty_raw.split(",")[0].replace(".", "")
        quantity = q

    # convert price per 1000 to per unit if possible
    price = 0.0
    if price_per_1000_raw and quantity:
        price_per_1000 = _to_float_eu(price_per_1000_raw)
        try:
            qty_val = float(quantity)
            price = round(price_per_1000 / 1000.0, 5)
        except Exception:
            price = price_per_1000

    line_value = _to_float_eu(total_raw) if total_raw else 0.0

    if customer_mat or desc:
        lines.append({
            "item_no": "10",
            "customer_product_no": customer_mat,
            "description": desc,
            "quantity": quantity,
            "uom": uom or "ST",
            "price": price,
            "line_value": line_value,
            "te_part_number": te_part,
            "manufacturer_part_no": "",
            "delivery_date": delivery_date,
        })

    return lines

def parse_sigmatek(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Sigmatek GmbH & Co KG",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
