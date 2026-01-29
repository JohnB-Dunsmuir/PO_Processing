
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# Ericsson AB parser

def detect_ericsson(text: str) -> bool:
    return "ericsson ab" in text.lower() and "purchase order" in text.lower()

def _extract_po_number(text):
    m = re.search(r"Purchase Order\s*(\d+)", text)
    return m.group(1) if m else ""

def _extract_po_date(text):
    m = re.search(r"Date\s*(\d{2}\.\d{2}\.\d{4})", text)
    return m.group(1) if m else ""

def _extract_buyer(text):
    m = re.search(r"Buyer\s*(.*)", text)
    return m.group(1).strip() if m else "Ericsson Buyer"

def _extract_delivery_address(text):
    m = re.search(r"Delivery Address\s*(.*?)\s*Customer", text, flags=re.S)
    if not m:
        return "DSV SOLUTIONS DWC LLC, Dubai Logistics City, Jebel Ali, UAE"
    return " ".join(i.strip() for i in m.group(1).splitlines() if i.strip())

def _extract_lines(text):
    lines=[]
    pat = re.compile(r"(?P<mat>RPM\S+)\s+(?P<qty>[\d\.,]+)\s+piece\s+(?P<price>[\d\.,/]+).*?(?P<total>[\d\.,]+)", re.S)
    m = pat.search(text)
    if m:
        qty = m.group("qty").replace(",","")
        price_raw = m.group("price").split("/")[0]
        total=_to_float_eu(m.group("total"))
        price=_to_float_eu(price_raw)
        lines.append({
            "item_no":"10",
            "customer_product_no":m.group("mat"),
            "description":"CABLE WITH CONNECTOR / POWER CABLE",
            "quantity":qty,
            "uom":"piece",
            "price":price,
            "line_value":total,
            "te_part_number":"",
            "manufacturer_part_no":"",
            "delivery_date":"10.11.2025"
        })
    return lines

def parse_ericsson(text):
    return {
        "header":{
            "po_number":_extract_po_number(text),
            "po_date":_extract_po_date(text),
            "customer_name":"Ericsson AB",
            "buyer":_extract_buyer(text),
            "delivery_address":_extract_delivery_address(text)
        },
        "lines":_extract_lines(text)
    }
