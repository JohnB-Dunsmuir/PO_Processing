import re
from typing import Any, Dict, List


REQUIRED_HEADER_KEYS = [
    "po_number",
    "po_date",
    "customer_name",
    "buyer",
    "delivery_address",
]


def detect_medical_po_29039309(text: str) -> bool:
    """
    ICU Medical Costa Rica bilingual PO format.
    Keep it fairly specific to avoid collisions with other medical PDFs.
    """
    if not text:
        return False
    t = text.upper()

    # Strong bilingual markers + ICU Medical + "ORDER / N" pattern
    return (
        ("PURCHASE ORDER" in t and "ORDER DE COMPRA" in t)
        and ("ICU MEDICAL" in t)
        and ("ORDER /" in t and "ORDEN" in t)
        and ("LINE ITEM/DESCRIPTION" in t or "LINEA DESCRIPCIÓN" in t)
    )


def parse_medical_po_29039309(text: str) -> Dict[str, Any]:
    if not text:
        return {"header": {}, "lines": []}

    # Normalize whitespace a bit (keep line breaks!)
    raw_lines = [ln.rstrip() for ln in text.splitlines()]
    lines_clean = [ln.strip() for ln in raw_lines]

    # -------------------------
    # HEADER
    # -------------------------
    header: Dict[str, Any] = {}

    # PO number: "ORDER / N ° ORDEN : 29039309REV#:0"
    m = re.search(r"ORDER\s*/\s*N\s*°?\s*ORDEN\s*:\s*([0-9]+)", text, re.IGNORECASE)
    if m:
        header["po_number"] = m.group(1).strip()
    else:
        header["po_number"] = "Not found"

    # PO date: "APPROVED DATE / FECHA : 08-JAN-26"
    m = re.search(r"APPROVED\s+DATE\s*/\s*FECHA\s*:\s*([0-9]{2}-[A-Z]{3}-[0-9]{2})", text, re.IGNORECASE)
    if m:
        header["po_date"] = m.group(1).strip()
    else:
        header["po_date"] = "Not found"

    # Buyer: "BUYER NAME / COMPRADOR : RocireneHerrera"
    m = re.search(r"BUYER\s+NAME\s*/\s*COMPRADOR\s*:\s*(.+)", text, re.IGNORECASE)
    if m:
        buyer_raw = m.group(1).strip()
        # very light cleanup: add space before a trailing LastName if jammed
        buyer_raw = re.sub(r"([a-z])([A-Z])", r"\1 \2", buyer_raw)
        header["buyer"] = buyer_raw.strip()
    else:
        header["buyer"] = "Not found"

    # Customer + delivery address block (Bill To / Facturar A ...)
    # We’ll take BILL TO block until FREIGHT TERM / DELIVERY.
    customer_name = "Not found"
    delivery_address = "Not found"

    bill_to_idx = None
    for i, ln in enumerate(lines_clean):
        if re.search(r"^BILL TO\s*/\s*FACTURAR A$", ln, re.IGNORECASE):
            bill_to_idx = i
            break

    if bill_to_idx is not None:
        addr_parts: List[str] = []
        for j in range(bill_to_idx + 1, min(bill_to_idx + 40, len(lines_clean))):
            stop = re.search(r"^(FREIGHT TERM|SHIP VIA|INCOTERMS|PAYMENT TERMS|DELIVERY)$", lines_clean[j], re.IGNORECASE)
            if stop:
                break
            if lines_clean[j]:
                addr_parts.append(lines_clean[j])

        # Customer name is usually first meaningful line in that block
        if addr_parts:
            customer_name = addr_parts[0].strip()

        # delivery_address: keep a short, useful version (avoid entire legal blob)
        delivery_address = " ".join(addr_parts[:6]).strip() if addr_parts else "Not found"

    header["customer_name"] = customer_name
    header["delivery_address"] = delivery_address

    # -------------------------
    # LINE ITEMS
    # -------------------------
    out_lines: List[Dict[str, Any]] = []

    # Find start of DELIVERY table
    start_idx = None
    for i, ln in enumerate(lines_clean):
        if ln.upper() == "DELIVERY":
            start_idx = i
            break

    if start_idx is not None:
        # Work only inside the delivery/table section
        table_region: List[str] = []
        for ln in lines_clean[start_idx:]:
            if re.search(r"^TOTAL\s*\(USD\)\s*:", ln, re.IGNORECASE):
                table_region.append(ln)
                break
            if re.search(r"^PURCHASE ORDER NUMBER MUST APPEAR", ln, re.IGNORECASE):
                break
            table_region.append(ln)

        # Item first row pattern:
        # "1 01 EM0000101 28-MAY-26 15-MAY-26 N 78600.00"
        item_row_re = re.compile(
            r"^\s*(\d+)\s+(\d+)\s+([A-Z0-9\-]+)\s+(\d{2}-[A-Z]{3}-\d{2})\s+(\d{2}-[A-Z]{3}-\d{2})\s+[YN]\s+([\d,]+\.\d{2})\s*$",
            re.IGNORECASE
        )

        # Tail row pattern (sometimes last desc line includes qty/uom/price):
        # "WRAPPED 15000 Each 5.2400"
        qty_tail_re = re.compile(
            r"^(?P<prefix>.*?)(?P<qty>\d+(?:\.\d+)?)\s+(?P<uom>EACH|EA|PCS|PC|UNIT|UNITS|EACH\.)\s+(?P<price>\d+(?:\.\d+)?)\s*$",
            re.IGNORECASE
        )

        i = 0
        while i < len(table_region):
            ln = table_region[i].strip()

            m = item_row_re.match(ln)
            if not m:
                i += 1
                continue

            item_no = m.group(1).strip()
            # rev = m.group(2).strip()  # available if you ever want it
            cust_part = m.group(3).strip()
            due_date = m.group(4).strip()
            # ship_date = m.group(5).strip()
            ext_price_raw = m.group(6).replace(",", "").strip()

            desc_parts: List[str] = []
            qty = None
            uom = None
            unit_price = None

            # Consume following lines until next item row or TOTAL
            i += 1
            while i < len(table_region):
                ln2 = table_region[i].strip()

                if item_row_re.match(ln2):
                    break
                if re.search(r"^TOTAL\s*\(USD\)\s*:", ln2, re.IGNORECASE):
                    break
                if not ln2:
                    i += 1
                    continue

                mt = qty_tail_re.match(ln2)
                if mt:
                    prefix = (mt.group("prefix") or "").strip().rstrip(",")
                    if prefix:
                        desc_parts.append(prefix)
                    qty = mt.group("qty")
                    uom = mt.group("uom").upper().replace(".", "")
                    unit_price = mt.group("price")
                    i += 1
                    # keep going just in case, but usually this is last meaningful row
                    continue

                # Normal description line
                desc_parts.append(ln2.strip().rstrip(","))
                i += 1

            description = " ".join([p for p in desc_parts if p]).strip()
            if description:
                # minor cleanup: collapse repeated commas/spaces
                description = re.sub(r"\s*,\s*", ", ", description)
                description = re.sub(r"\s{2,}", " ", description)

            # Build line dict
            line: Dict[str, Any] = {
                "item_no": item_no,
                "customer_product_no": cust_part or "Not found",
                "te_part_number": "Not found",
                "manufacturer_part_no": cust_part or "Not found",
                "description": description or "Not found",
                "quantity": str(qty) if qty is not None else "Not found",
                "uom": (uom if uom else "Not found"),
                "price": float(unit_price) if unit_price is not None else None,
                "line_value": float(ext_price_raw) if ext_price_raw else None,
                "delivery_date": due_date or "Not found",
            }

            out_lines.append(line)

    # If we still have nothing, return a single safe placeholder line (contract)
    if not out_lines:
        out_lines = [{
            "item_no": "1",
            "customer_product_no": "Not found",
            "te_part_number": "Not found",
            "manufacturer_part_no": "Not found",
            "description": "Not found",
            "quantity": "1",
            "uom": "EA",
        }]

    return {"header": header, "lines": out_lines}
