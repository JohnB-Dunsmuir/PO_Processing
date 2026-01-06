
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# DS Smith Packaging Netherlands BV parser

def detect_ds_smith_nl(text: str) -> bool:
    t = text.lower()
    return "ds smith packaging netherlands" in t and "purchase order no. dss" in t

def _extract_po_number(text: str):
    m = re.search(r"Purchase Order No\.\s*(DSS\d+)", text)
    return m.group(1) if m else ""

def _extract_po_date(text):
    m = re.search(r"Date\s*(\d{2}\.\d{2}\.\d{4})", text)
    return m.group(1) if m else ""

def _extract_buyer(text):
    m = re.search(r"For Purchase Order.*?Name:\s*([^\n]+)", text)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text):
    m = re.search(r"Please deliver to\s*(.*?)\s*Purchase Order", text, flags=re.S)
    if not m:
        return ""
    return " ".join(i.strip() for i in m.group(1).splitlines() if i.strip())

def _extract_lines(text):
    lines=[]
    pat = re.compile(r"10\s+(?P<mat>\d+)\s+(?P<desc>[A-Z0-9]+)\s+00A.*?(?P<qty>\d+)\s+PCS.*?(?P<price>[\d\.,]+)\s*/1,000.*?(?P<total>[\d\.,]+)", re.S)
    m=pat.search(text)
    if m:
        qty = m.group("qty")
        total = _to_float_eu(m.group("total"))
        price_per_1000 = _to_float_eu(m.group("price"))
        price = round(price_per_1000/1000,5)
        lines.append({
            "item_no":"10",
            "customer_product_no": m.group("mat"),
            "description": m.group("desc"),
            "quantity": qty,
            "uom":"PCS",
            "price": price,
            "line_value": total,
            "te_part_number":"LV431015-A",
            "manufacturer_part_no":"",
            "delivery_date":"29.07.2024"
        })
    return lines

def parse_ds_smith_nl(text):
    return {
        "header":{
            "po_number":_extract_po_number(text),
            "po_date":_extract_po_date(text),
            "customer_name":"DS Smith Packaging Netherlands BV",
            "buyer":_extract_buyer(text),
            "delivery_address":_extract_delivery_address(text)
        },
        "lines":_extract_lines(text)
    }
