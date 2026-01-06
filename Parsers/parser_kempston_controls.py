
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# Kempston Controls UK parser

def detect_kempston_controls(text: str) -> bool:
    return "kempston controls" in text.lower() and "purchase order" in text.lower()

def _extract_po_number(text):
    m = re.search(r"Purchase Order No\..*?(PO\d+)", text)
    return m.group(1) if m else ""

def _extract_po_date(text):
    m = re.search(r"Date\s*(\d{2}/\d{2}/\d{4})", text)
    if m:
        d,mn,y = m.group(1).split("/")
        return f"{d}.{mn}.{y}"
    return ""

def _extract_buyer(text):
    return "Kempston Controls Buyer"

def _extract_delivery_address(text):
    return "Kempston Controls Distribution Centre, Unit D4 Baron Avenue, Earls Barton, Northamptonshire NN6 0JE, UK"

def _extract_lines(text):
    lines=[]
    pat = re.compile(r"(?P<item>\d+)\s+(?P<code>1S[A-Z0-9]+)\s.*?EACH\s+(?P<qty>[\d,]+)\s+£(?P<price>[\d\.]+)\s+£(?P<total>[\d\.]+)")
    for m in pat.finditer(text):
        qty = m.group("qty").replace(",","")
        lines.append({
            "item_no":str(int(m.group("item"))*10),
            "customer_product_no":m.group("code"),
            "description":"",
            "quantity":qty,
            "uom":"EACH",
            "price":_to_float_eu(m.group("price")),
            "line_value":_to_float_eu(m.group("total")),
            "te_part_number":m.group("code"),
            "manufacturer_part_no":"",
            "delivery_date":"27.06.2025"
        })
    return lines

def parse_kempston_controls(text):
    return {
        "header":{
            "po_number":_extract_po_number(text),
            "po_date":_extract_po_date(text),
            "customer_name":"Kempston Controls",
            "buyer":_extract_buyer(text),
            "delivery_address":_extract_delivery_address(text)
        },
        "lines":_extract_lines(text)
    }
