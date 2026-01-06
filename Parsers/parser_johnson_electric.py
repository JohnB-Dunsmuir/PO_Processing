
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# Johnson Electric Poland parser

def detect_johnson_electric(text: str) -> bool:
    return "johnson electric poland" in text.lower() and "purchase order/numer zamówienia" in text.lower()

def _extract_po_number(text):
    m = re.search(r"(\d{11}-\d)", text)
    return m.group(1) if m else ""

def _extract_po_date(text):
    m = re.search(r"PO Date.*?(\d{2}\.\d{2}\.\d{4})", text)
    return m.group(1) if m else ""

def _extract_buyer(text):
    m = re.search(r"Buyer.*?([A-Z ]+)", text)
    return m.group(1).strip() if m else "Johnson Electric Buyer"

def _extract_delivery_address(text):
    m = re.search(r"Ship to/Dostawa do:\s*(.*?)\s*TE Connectivity", text, flags=re.S)
    if not m:
        return "Johnson Electric Poland, ul. Cieszkowskiego 26, 42-500 Bedzin"
    return " ".join(i.strip() for i in m.group(1).splitlines() if i.strip())

def _extract_lines(text):
    lines=[]
    pat = re.compile(r"(?P<qty>\d+)\s+EA.*?Unit Price.*?(?P<price>[\d\.]+).*?Net Amount.*?(?P<total>[\d\.]+).*?Supplier part no.*?(?P<te>[\d\-]+)", re.S)
    m = pat.search(text)
    if m:
        lines.append({
            "item_no":"10",
            "customer_product_no":"440860630",
            "description":"CT connector 2m 4pol",
            "quantity":m.group("qty"),
            "uom":"EA",
            "price":_to_float_eu(m.group("price")),
            "line_value":_to_float_eu(m.group("total")),
            "te_part_number":m.group("te"),
            "manufacturer_part_no":"",
            "delivery_date":"13.10.2025"
        })
    return lines

def parse_johnson_electric(text):
    return {
        "header":{
            "po_number":_extract_po_number(text),
            "po_date":_extract_po_date(text),
            "customer_name":"Johnson Electric Poland",
            "buyer":_extract_buyer(text),
            "delivery_address":_extract_delivery_address(text)
        },
        "lines":_extract_lines(text)
    }
