
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# SIRAIL SAS parser

def detect_sirail(text):
    return "sirail sas" in text.lower() and "commande" in text.lower()

def _extract_po_number(text):
    m=re.search(r"COMMANDE N\s*:\s*(\S+)",text)
    return m.group(1) if m else ""

def _extract_po_date(text):
    m=re.search(r"Date\s*:\s*(\d{2}/\d{2}/\d{4})",text)
    if m:
        d,mn,y=m.group(1).split("/")
        return f"{d}.{mn}.{y}"
    return ""

def _extract_buyer(text):
    return "Imed CHTIOUI"

def _extract_delivery_address(text):
    return "SIRAIL SAS, Zone la Bastide, 48500 La Canourgue, France"

def _extract_lines(text):
    lines=[]
    pat=re.compile(r"(?P<qty>[\d\.,]+)\s+UN\s+\d+\s+(?P<desc>.+?)\s+(?P<art>\d{8})\s+(?P<date>\d{2}/\d{2}/\d{4})\s+(?P<price>[\d\.,]+)\s+(?P<total>[\d\.,]+)",re.S)
    for i,m in enumerate(pat.finditer(text),start=1):
        qty=m.group("qty").replace(",","")
        lines.append({
            "item_no":str(i*10),
            "customer_product_no":m.group("art"),
            "description":m.group("desc").strip(),
            "quantity":qty,
            "uom":"UN",
            "price":_to_float_eu(m.group("price")),
            "line_value":_to_float_eu(m.group("total")),
            "te_part_number":"",
            "manufacturer_part_no":"",
            "delivery_date":m.group("date").replace("/",".")
        })
    return lines

def parse_sirail(text):
    return {
        "header":{
            "po_number":_extract_po_number(text),
            "po_date":_extract_po_date(text),
            "customer_name":"SIRAIL SAS",
            "buyer":_extract_buyer(text),
            "delivery_address":_extract_delivery_address(text)
        },
        "lines":_extract_lines(text)
    }
