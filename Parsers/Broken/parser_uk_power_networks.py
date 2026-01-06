import re

# ------------------------------------------------------------
# DETECTION
# ------------------------------------------------------------
def detect_uk_power_networks(text: str) -> bool:
    """
    Detects UK Power Networks purchase orders.
    """
    if not text:
        return False

    triggers = [
        "UK Power Networks",
        "Order number",
        "Vendor ID",
        "Accounts Payable PO Box 1184",
        "Please quote this Purchase Order Number",
    ]

    return any(t.lower() in text.lower() for t in triggers)


# ------------------------------------------------------------
# PARSE
# ------------------------------------------------------------
def parse_uk_power_networks(text: str):
    """
    Parse a UK Power Networks PO into unified header+lines format.
    """

    header = {}
    lines = []

    # ------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------

    # PO Number
    m = re.search(r'Order number\s*([0-9]+)', text)
    header["po_number"] = m.group(1) if m else ""

    # PO Date
    m = re.search(r'Date\s*([0-9]{2}\/[0-9]{2}\/[0-9]{4})', text)
    header["po_date"] = m.group(1) if m else ""

    # Buyer name (Contact)
    m = re.search(r'Contact\s*\/\s*Phone\s*([A-Za-z ]+)\s*\/', text)
    header["buyer"] = m.group(1).strip() if m else ""

    # Customer name
    header["customer_name"] = "UK Power Networks"

    # Delivery Date
    m = re.search(r'Delivery date\s*([0-9]{2}\/[0-9]{2}\/[0-9]{4})', text)
    delivery_date = m.group(1) if m else ""
    header["delivery_date"] = delivery_date

    # Delivery Address
    m = re.search(
        r'Delivery address\s*(UK PN[\s\S]+?)(Page|Item)',
        text
    )
    if m:
        addr = m.group(1)
        addr = addr.replace("\n", " ").strip()
        header["delivery_address"] = addr
    else:
        header["delivery_address"] = ""

    # ------------------------------------------------------------
    # LINE ITEM
    # ------------------------------------------------------------
    #
    # Table structure (single line):
    #
    # 10 02758J 40.00 KIT 36.66 1,466.40
    #

    line_pattern = re.compile(
        r'(\d+)\s+'            # Item
        r'([A-Za-z0-9]+)\s+'   # Material
        r'([\d\.]+)\s+'        # Quantity
        r'([A-Z]+)\s+'         # UM
        r'([\d\.]+)\s+'        # Net price
        r'([\d\.,]+)',         # Net amount
        re.M
    )

    # Description: multiline block
    desc_pattern = re.compile(
        r'(\d+)\s+[A-Za-z0-9]+\s+[\d\.]+\s+[A-Z]+\s+[\d\.]+\s+[\d\.,]+\s+([\s\S]+?)Total',
        re.M
    )

    desc_match = desc_pattern.search(text)
    long_description = ""
    if desc_match:
        long_description = " ".join(desc_match.group(2).split())

    for m in line_pattern.finditer(text):
        item = m.group(1)
        material = m.group(2)
        qty = m.group(3)
        uom = m.group(4)
        price = m.group(5)
        line_value = m.group(6).replace(",", "")

        lines.append({
            "item_no": item,
            "customer_product_no": material,
            "description": long_description or material,
            "quantity": qty,
            "price": price,
            "line_value": line_value,
            "customer_material_no": "",
            "revision": "",
            "order_item": item,
            "delivery_date": delivery_date,
            "te_part_number": material,
            "customer_order_no": ""
        })

    return {
        "header": header,
        "lines": lines
    }
