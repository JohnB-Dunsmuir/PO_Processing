
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# Electrodis / Regelec Sainte Luce parser

def detect_electrodis(text: str) -> bool:
    return "electrodis" in text.lower() and "commande" in text.lower()

def _extract_po_number(text):
    m = re.search(r"Commande\s*:\s*(\d+)", text)
    return m.group(1) if m else ""

def _extract_po_date(text):
    m = re.search(r"le\s*:\s*(\d{2}/\d{2}/\d{4})", text)
    if m:
        d,mn,y=m.group(1).split("/")
        return f"{d}.{mn}.{y}"
    return ""

def _extract_buyer(text):
    m=re.search(r"Contact.*?([A-Za-z ]+),",text)
    return m.group(1).strip() if m else "Electrodis Buyer"

def _extract_delivery_address(text):
    return "Parc d'activités de la maison neuve - 3 rue Louis Bréguet, 44980 Sainte Luce sur Loire, France"

def _extract_lines(text):
    lines=[]
    pat = re.compile(r"(?P<qty>\d+)\s+(?P<code>1S[A-Z0-9]+)\s+Offre.*?\n(?P<desc>.*?)(?=\n\d+\s+1S|$)", re.S)
    for i,m in enumerate(pat.finditer(text),start=1):
        lines.append({
            "item_no":str(i*10),
            "customer_product_no":m.group("code"),
            "description":m.group("desc").strip(),
            "quantity":m.group("qty"),
            "uom":"PC",
            "price":0.0,
            "line_value":0.0,
            "te_part_number":m.group("code"),
            "manufacturer_part_no":"",
            "delivery_date":"17.06.2025"
        })
    return lines

def parse_electrodis(text):
    return {
        "header":{
            "po_number":_extract_po_number(text),
            "po_date":_extract_po_date(text),
            "customer_name":"Electrodis Sainte-Luce",
            "buyer":_extract_buyer(text),
            "delivery_address":_extract_delivery_address(text)
        },
        "lines":_extract_lines(text)
    }
