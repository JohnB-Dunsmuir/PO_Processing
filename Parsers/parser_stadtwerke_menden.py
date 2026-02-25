import re


def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))


def detect_stadtwerke_menden(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "stadtwerke menden gmbh" in t and "bestellung" in t


def _extract_po_number(text: str) -> str:
    m = re.search(r"\b(\d{8})\b\s+\d{2}\.\d{2}\.\d{4}", text)
    return m.group(1) if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"\b\d{8}\b\s+(\d{2}\.\d{2}\.\d{4})", text)
    return m.group(1) if m else ""


def _extract_buyer(text: str) -> str:
    m = re.search(
        r"AnsprechpartnerIn\s*Telefon\s*\n.*?\s+([A-Za-zäöüÄÖÜß\-]+\s+[A-Za-zäöüÄÖÜß\-]+)\s+\d{6,}",
        text,
        flags=re.S
    )
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    m = re.search(
        r"Bitte liefern Sie an:\s*(Stadtwerke Menden GmbH.*?DEUTSCHLAND)",
        text,
        flags=re.I | re.S,
    )
    if not m:
        return "Stadtwerke Menden GmbH, Am Papenbusch 8-10, 58708 Menden, Deutschland"

    block = m.group(1)
    return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())


def _extract_lines(text: str):
    results = []

    pattern = re.compile(
        r"(?P<pos>\d{5})\s+"
        r"(?P<mat>\d+)\s+"
        r"(?P<qty>\d+)\s+St[üu]ck\s+"
        r"(?P<price>[\d\.,]+)\s+EUR\/1 ST\s+"
        r"(?P<total>[\d\.,]+)",
        flags=re.I,
    )

    matches = list(pattern.finditer(text))

    for idx, m in enumerate(matches):

        position = m.group("pos")
        material = m.group("mat")
        qty_raw = m.group("qty")
        price_raw = m.group("price")
        total_raw = m.group("total")

        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[start:end]

        desc_lines = []
        for ln in block.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            if ln.startswith("Ihre Materialnr."):
                break
            if ln.startswith("Bruttopreis"):
                break
            if ln.startswith("Gesamtnettowert"):
                break
            desc_lines.append(ln)

        description = " ".join(desc_lines).strip()

        m_te = re.search(r"Ihre Materialnr\.\s*(\S+)", block, flags=re.I)
        te_part = m_te.group(1).strip() if m_te else ""

        results.append({
            "item_no": position,
            "ship_to": "XX",
            "customer_product_no": material,
            "te_part_number": te_part,
            "manufacturer_part_no": te_part,
            "description": description,
            "quantity": float(qty_raw),
            "uom": "ST",
            "price": _to_float_eu(price_raw),
            "line_value": _to_float_eu(total_raw),
            "delivery_date": "",
        })

    return results


def parse_stadtwerke_menden(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Stadtwerke Menden GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)

    return {"header": header, "lines": lines}