import re

# Shared EU number normalization
def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    s = num.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0


# Canonical Ship-To normalisation (same as main dispatcher)
CANONICAL_ADDRESSES = {
    "POZNANSKA 1C": "KIMBALL ELECTRONICS POLAND, SP. Z O.O., POZNANSKA 1C, PL-62-080 TARNOWO PODGORNE",
}


# -------------------------------------------------------------
# Legacy Ship-to extraction
# -------------------------------------------------------------
def extract_ship_to_address_legacy(text: str) -> str:
    """
    Extracts the legacy Kimball Ship-To block:
      Ship To: .... Bill To:
    """
    m = re.search(r"Ship To:\s*(.*?)Bill To:", text, flags=re.S | re.I)
    if not m:
        m = re.search(r"Ship To:\s*(.*?)(?:Page|\Z)", text, flags=re.S | re.I)

    if not m:
        return ""

    block = m.group(1)
    block_up = block.upper()

    # If block contains known canonical signature, use canonical
    for key, canonical in CANONICAL_ADDRESSES.items():
        if key in block_up:
            return canonical

    # Otherwise return flattened block
    return " ".join(line.strip() for line in block.splitlines() if line.strip())


# -------------------------------------------------------------
# Legacy PO Number
# -------------------------------------------------------------
def extract_po_number_legacy(text: str) -> str:
    m = re.search(r"\bPO Number\s*[: ]+\s*(\d+)", text, flags=re.I)
    if m:
        return m.group(1)

    # fallback: longest digit string
    m = re.search(r"\b(\d{8,10})\b", text)
    return m.group(1) if m else ""


# -------------------------------------------------------------
# Legacy PO Date
# -------------------------------------------------------------
def extract_po_date_legacy(text: str) -> str:
    m = re.search(r"\bPO Date\s*[: ]+(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    if m:
        return m.group(1)

    m = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
    return m.group(1) if m else ""


# -------------------------------------------------------------
# Legacy Buyer
# -------------------------------------------------------------
def extract_buyer_legacy(text: str) -> str:
    m = re.search(r"Buyer\s*(.*?)\n", text)
    if m:
        val = m.group(1).strip()
        if val:
            return val

    if "P. WIEDERA" in text.upper():
        return "P. Wiedera"

    return ""


# -------------------------------------------------------------
# Legacy Line Item Parser (Format A)
# -------------------------------------------------------------
def extract_line_item_legacy(text: str) -> dict:
    """
    Legacy Kimball Format A structure:

    - Customer PN:   1234-5678-9012
    - TE PN:         X-1234567-X
    - Qty:           10.890 EA
    - Price:         12,34
    - Line Value:    123,45
    - Description:   First non-empty line after PN
    """

    # Customer PN: 4-4-4 digits with dashes
    cust_match = re.search(r"(\d{4}-\d{4}-\d{4})", text)
    cust = cust_match.group(1) if cust_match else ""

    # Description = first non-empty line after PN
    desc = ""
    if cust_match:
        tail = text[cust_match.end(): cust_match.end() + 300]
        for line in tail.splitlines():
            ln = line.strip()
            if ln:
                desc = ln
                break

    # Quantity + UOM
    qty = ""
    uom = ""
    m_qty = re.search(r"(\d{1,3}(?:\.\d{3})*)\s*(EA|PCS?)", text, flags=re.I)
    if m_qty:
        qty = m_qty.group(1).replace(".", "")
        uom = m_qty.group(2).upper()

    # Price & Line Value: first 2 EU numbers
    money_pattern = r"(\d{1,3}(?:\.\d{3})*,\d{2})"
    money_values = re.findall(money_pattern, text)

    price = _to_float_eu(money_values[0]) if len(money_values) >= 1 else 0.0
    line_value = _to_float_eu(money_values[1]) if len(money_values) >= 2 else 0.0

    # TE PN pattern: X-1234567-X
    m_te = re.search(r"(\d-\d{7}-\d)", text)
    te = m_te.group(1) if m_te else ""

    # Delivery date
    m_dd = re.search(r"Delivery date[: ]+(\d{2}\.\d{2}\.\d{4})",
                     text, flags=re.I)
    dd = m_dd.group(1) if m_dd else ""

    return {
        "item_no": "10",
        "customer_product_no": cust,
        "description": desc,
        "quantity": qty,
        "uom": uom,
        "price": price,
        "line_value": line_value,
        "te_part_number": te,
        "manufacturer_part_no": te,
        "delivery_date": dd,
    }


# -------------------------------------------------------------
# FINAL LEGACY PARSE FUNCTION
# -------------------------------------------------------------
def parse_kimball_legacy(text: str) -> dict:
    """
    Returns full header + lines for the old Kimball Format A POs.
    """
    header = {
        "po_number": extract_po_number_legacy(text),
        "po_date": extract_po_date_legacy(text),
        "customer_name": "Kimball Electronics Poland",
        "buyer": extract_buyer_legacy(text),
        "delivery_address": extract_ship_to_address_legacy(text),
    }

    line = extract_line_item_legacy(text)
    return {"header": header, "lines": [line] if line.get("quantity") else []}
