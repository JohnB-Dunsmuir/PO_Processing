# Parsers/parser_sse_stock.py
# Parser for SSE Stock Ltd Purchase Orders
# Works with unified process_purchase_orders.py
# Detects SSE Stock Ltd / SSE plc POs and emits standardized RPA output

import re
import os

def detect_sse_stock(text: str) -> bool:
    """
    Detects SSE Stock Ltd purchase orders.
    Triggers on:
      - 'SSE Stock Ltd' or 'SSE LOGISTICS CENTRE'
      - '@sse.com' email domain
      - 'Standard Purchase Order' or 'Order Date' in the header
    """
    t = (text or "").upper()
    return any([
        "SSE STOCK LTD" in t,
        "SSE LOGISTICS CENTRE" in t,
        "@SSE.COM" in t,
        "STANDARD PURCHASE ORDER" in t
    ])


def parse_sse_stock(text: str, source_file: str = "") -> list:
    """
    Extracts SSE Stock Ltd PO data into the unified RPA schema.
    Produces a list of line-item dicts matching TLA Distribution Order Entry Automation headers.
    """
    source_name = os.path.basename(source_file)
    results = []

    # --- HEADER EXTRACTION ---
    po_number = _search(r"Order\s*([0-9]{10})", text)
    po_date = _search(r"Order Date\s*([0-9]{2}\-[A-Z]{3}\-[0-9]{4})", text)
    buyer = _search(r"Buyer\s*([A-Za-z,.\s]+)", text)
    currency = "GBP"
    delivery_address = _extract_ship_to(text)
    order_type = _search(r"Type\s*([A-Za-z\s]+Order)", text)

    # --- LINE ITEM EXTRACTION ---
    pattern = re.compile(
        r"(?P<item>\d+)\s+(?P<stock>\d+)\s+Required By:\s*(?P<qty>\d+)\s+(?P<uom>[A-Z]+)\s+(?P<price>[\d\.,]+)\s+(?P<total>[\d\.,]+)\s*(?:Supplier Item:(?P<tecode>[A-Za-z0-9\-\s]+))?",
        re.MULTILINE
    )

    for match in pattern.finditer(text):
        desc = _extract_description_after(text, match.group("stock"))
        delivery_date = _search_after(text, match.group("stock"), r"([0-9]{2}\-[A-Z]{3}\-[0-9]{4})")
        results.append({
            "Purchase Order": po_number or "",
            "Date on PO": po_date or "",
            "Source.Name": source_name,
            "Quantity": match.group("qty"),
            "UoM": match.group("uom"),
            "Customer Product number": match.group("stock"),
            "Description": desc,
            "TE Product No.": (match.group("tecode") or "").strip(),
            "Manufacturer's Part No.": "",
            "Delivery Date": delivery_date or "",
            "Currency": currency,
            "Net Price": match.group("price"),
            "Total Net Value": match.group("total"),
            "Item Number": match.group("item"),
            "Distribution Channel": "",
            "Sales Org": "",
            "Bl": "",
            "Ship to ID": "",
            "Sold to Number": "",
            "Order Type": order_type or "",
            "Buyer": buyer or "",
            "Delivery Address": delivery_address,
            "Relevant dummy part number": ""
        })

    return results


# -------------------- helpers --------------------

def _search(pattern: str, text: str) -> str:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def _search_after(text: str, anchor: str, pattern: str) -> str:
    """Searches for a regex pattern occurring after a specific stock number anchor."""
    idx = text.find(anchor)
    if idx == -1:
        return ""
    snippet = text[idx: idx + 200]
    m = re.search(pattern, snippet)
    return m.group(1).strip() if m else ""

def _extract_description_after(text: str, stock_number: str) -> str:
    """Extracts the line following the stock number as the item description."""
    pattern = re.compile(rf"{stock_number}[^\n]*\n([A-Z0-9][^\n]+)", re.IGNORECASE)
    m = pattern.search(text)
    if m:
        desc = m.group(1)
        # clean if it includes unwanted fields like 'This line references...'
        desc = re.sub(r"This line references.*", "", desc).strip()
        return desc
    return ""

def _extract_ship_to(text: str) -> str:
    """Extracts the 'Ship To' block for delivery address."""
    addr = re.search(r"Ship To:\s*([A-Za-z0-9 ,\.\-\n]+?)Bill To:", text, re.IGNORECASE)
    if addr:
        return addr.group(1).replace("\n", " ").strip()
    return ""

# Example usage
# if __name__ == "__main__":
#     with open("/mnt/data/SSE Stock Ltd.pdf.txt", "r", encoding="utf-8") as f:
#         text = f.read()
#     data = parse_sse_stock(text, source_file="SSE Stock Ltd.pdf")
#     import json
#     print(json.dumps(data, indent=2, ensure_ascii=False))


def detect_sse_stock(text: str) -> bool:
    # Detects Sse Stock purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "SSE STOCK" in t,                 # company name
        "@SSESTOCK.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
