import re

# ---------------------------------------------------------------------------
# DETECTION
# ---------------------------------------------------------------------------

def detect_wolseley_uk(text: str) -> bool:
    """
    Detect Wolseley UK POs.
    Very stable, based on unique header markers.
    """
    if not text:
        return False

    t = text.lower()
    triggers = [
        "wolseley uk limited",
        "document ref:",
        "raised date:",
        "jointing tech",
        "supplier: tycoel",
    ]
    return any(trig in t for trig in triggers)


# ---------------------------------------------------------------------------
# HEADER HELPERS
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    # Wolseley does not show a formal PO number → use Document Ref
    m = re.search(r"Document Ref:\s*([A-Za-z0-9\/\-\_]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    # Example: "Raised Date: 28 Aug 2025"
    m = re.search(r"Raised Date:\s*([0-9A-Za-z ]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    """
    Delivery block appears under:

        Deliveries To: JT1
        JOINTING TECH - WOKING
        UNIT 19 WOKING BUSINESS P
        ALBERT DRIVE
        WOKING
        SURREY, GU21 5JY
        TBC

    End before the table header "Product Code"
    """
    m = re.search(
        r"Deliveries To:\s*JT1\s*([\s\S]*?)Product Code",
        text,
        flags=re.I,
    )
    if not m:
        return ""
    block = m.group(1)
    flat = " ".join(line.strip() for line in block.splitlines() if line.strip())
    return flat


# ---------------------------------------------------------------------------
# LINE PARSING
# ---------------------------------------------------------------------------

def _extract_lines(text: str):
    """
    Parse table lines.
    Table structure (confirmed from PDF):

        Product Code | Supplier Code | Description | UOM | Qty | Notes/Price

    UOM column is visually present but blank for these examples.
    Price is shown as "£69.93" or "£1.63".
    """

    # Pattern capturing:
    # 1 = product code
    # 2 = supplier code
    # 3 = description (greedy but stops before qty)
    # 4 = quantity
    # 5 = price (stripped of £)
    regex = re.compile(
        r"([A-Za-z0-9\/\-\(\)]+)\s+"           # Product Code
        r"([A-Za-z0-9\/\-\(\)]+)\s+"           # Supplier Code
        r"([A-Za-z0-9 ,\/\-\(\)\.]+?)\s+"      # Description
        r"(\d+)\s+"                             # Qty
        r"£?([\d\.]+)",                         # Price
        flags=re.M
    )

    lines = []

    for m in regex.finditer(text):
        product_code = m.group(1).strip()
        supplier_code = m.group(2).strip()
        description = " ".join(m.group(3).split())
        qty = m.group(4).strip()
        price = m.group(5).strip()

        lines.append({
            "item_no": product_code,
            "customer_product_no": product_code,
            "description": description,
            "quantity": qty,
            "uom": "",                         # UOM column is blank in Wolseley PDF
            "price": price,                    # Price/Unit
            "line_value": "",                  # Wolseley does not show totals
            "te_part_number": supplier_code,   # best available TE mapping
            "manufacturer_part_no": supplier_code,
            "delivery_date": "",               # No delivery date shown
        })

    return lines


# ---------------------------------------------------------------------------
# PARSER ENTRYPOINT
# ---------------------------------------------------------------------------

def parse_wolseley_uk(text: str) -> dict:
    """
    Return full header + lines dict for unified engine v11.3.2.
    """

    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Wolseley UK Limited",
        "buyer": "",
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)

    return {
        "header": header,
        "lines": lines,
    }
