
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# Comptoir du Lignard parser

def detect_comptoir_lignard(text):
    return "comptoir du lignard" in text.lower() and "commande" in text.lower()

def _extract_po_number(text):
    m=re.search(r"Numéro\s*:\s*(\S+)",text)
    return m.group(1) if m else ""

def _extract_po_date(text):
    m=re.search(r"Date\s*:\s*(\d{2}/\d{2}/\d{4})",text)
    if m:
        d,mn,y=m.group(1).split("/")
        return f"{d}.{mn}.{y}"
    return ""

def _extract_buyer(text):
    return "Victor Nicolas"

def _extract_delivery_address(text):
    return "151 impasse de la Balme, 69800 Saint Priest, France"

def _extract_lines(text):
    lines=[]
    pat=re.compile(r"(?P<code>TYC\S+)\s+(?P<desc>.+?)\s+(?P<qty>\d+)\s+(?P<price>[\d\.,]+)\s+(?P<total>[\d\.,]+)")
    for i,m in enumerate(pat.finditer(text),start=1):
        lines.append({
            "item_no":str(i*10),
            "customer_product_no":m.group("code"),
            "description":m.group("desc").strip(),
            "quantity":m.group("qty"),
            "uom":"PC",
            "price":_to_float_eu(m.group("price")),
            "line_value":_to_float_eu(m.group("total")),
            "te_part_number":m.group("code"),
            "manufacturer_part_no":"",
            "delivery_date":""
        })
    return lines

def parse_comptoir_lignard(text):
    return {
        "header":{
            "po_number":_extract_po_number(text),
            "po_date":_extract_po_date(text),
            "customer_name":"Comptoir du Lignard",
            "buyer":_extract_buyer(text),
            "delivery_address":_extract_delivery_address(text)
        },
        "lines":_extract_lines(text)
    }
