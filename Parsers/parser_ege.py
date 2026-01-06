
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# EGE Einkaufsgenossenschaft parser

def detect_ege(text):
    t=text.lower()
    return "ege-einkaufsgenossenschaft" in t or "österr. elektrizitätswerke" in t

def _extract_po_number(text):
    m=re.search(r"Belegnummer:\s*(\d+)",text)
    return m.group(1) if m else ""

def _extract_po_date(text):
    m=re.search(r"Belegdatum:\s*(\d{2}\.\d{2}\.\d{4})",text)
    return m.group(1) if m else ""

def _extract_buyer(text):
    return "EGE Einkauf"

def _extract_delivery_address(text):
    m=re.search(r"ENERGIE RIED.*?Ried i\.I\.",text,re.S)
    if m:
        return "ENERGIE RIED Ges.m.b.H., Kellergasse 10, 4910 Ried im Innkreis, Austria"
    return "EGE Delivery Address"

def _extract_lines(text):
    lines=[]
    pat=re.compile(r"(?P<code>[A-Z0-9\-]+)\s+1,00\s+STK\s+(?P<price>[\d\.,]+).*?LT:\s*(?P<date>\d{2}\.\d{2}\.\d{4})",re.S)
    for i,m in enumerate(pat.finditer(text),start=1):
        total=_to_float_eu(m.group("price"))
        lines.append({
            "item_no":str(i*10),
            "customer_product_no":m.group("code"),
            "description":"",
            "quantity":"1",
            "uom":"STK",
            "price":total,
            "line_value":total,
            "te_part_number":m.group("code"),
            "manufacturer_part_no":"",
            "delivery_date":m.group("date")
        })
    return lines

def parse_ege(text):
    return {
        "header":{
            "po_number":_extract_po_number(text),
            "po_date":_extract_po_date(text),
            "customer_name":"EGE Einkaufsgenossenschaft",
            "buyer":_extract_buyer(text),
            "delivery_address":_extract_delivery_address(text)
        },
        "lines":_extract_lines(text)
    }
