import re
from typing import Dict, List, Any, Optional


def detect_wolseley_uk(text: str) -> bool:
    if not text:
        return False
    return "WOLSELEY UK LIMITED" in text.upper()


REQUIRED_HEADER_KEYS = ["po_number", "po_date", "customer_name", "buyer", "delivery_address"]


def _nf(v: Optional[str]) -> str:
    if v is None:
        return "Not found"
    s = str(v).strip()
    return s if s else "Not found"


def parse_wolseley_uk(text: str) -> Dict[str, Any]:
    header = {
        "po_number": "Not found",
        "po_date": "Not found",
        "customer_name": "Wolseley UK Limited",
        "buyer": "Not found",
        "delivery_address": "Not found",
    }

    header["po_number"] = _nf(
        re.search(r"Document Ref:\s*([A-Z0-9/]+)", text).group(1)
        if re.search(r"Document Ref:\s*([A-Z0-9/]+)", text)
        else None
    )

    header["po_date"] = _nf(
        re.search(r"Raised Date:\s*(\d{2}\s\w+\s\d{4})", text).group(1)
        if re.search(r"Raised Date:\s*(\d{2}\s\w+\s\d{4})", text)
        else None
    )

    delivery = re.search(r"Deliveries To:\s*(JT1.*?SURREY.*?JY)", text, re.DOTALL)
    header["delivery_address"] = _nf(delivery.group(1) if delivery else None)

    lines = []
    for m in re.finditer(r"(CJ\d+).*?(\d+)\s+£([\d.]+)", text):
        lines.append({
            "item_no": m.group(1),
            "te_part_number": m.group(1),
            "description": m.group(1),
            "quantity": m.group(2),
            "uom": "EA",
        })

    if not lines:
        lines.append({
            "item_no": "1",
            "te_part_number": "Not found",
            "description": "Not found",
            "quantity": "1",
            "uom": "EA",
        })

    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": lines}
