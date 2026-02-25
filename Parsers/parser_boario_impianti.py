import re


def detect_boario_impianti(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return (
        "ordine a fornitore" in t
        and "boario impianti" in t
    )


def _extract_po_number(text: str) -> str:
    m = re.search(r"\n([0-9]+\/[0-9]{4})\s+\d{2}\/\d{2}\/\d{4}", text)
    return m.group(1) if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"[0-9]+\/[0-9]{4}\s+(\d{2}\/\d{2}\/\d{4})", text)
    return m.group(1).replace("/", ".") if m else ""


def _to_float_eu(value: str) -> float:
    return float(value.replace(".", "").replace(",", "."))


def _extract_lines(text: str):
    lines = text.splitlines()
    results = []

    in_table = False
    item_no = 1

    for i in range(len(lines)):
        line = lines[i].strip()

        if "CODICE ARTICOLO" in line.upper():
            in_table = True
            continue

        if not in_table:
            continue

        if line.upper().startswith("TOTALE ORDINE"):
            break

        m = re.match(
            r"^([A-Z0-9]+)\s+(.+?)\s+([A-Za-z]+)\s+(\d+)\s+€\s*([\d\.,]+)\s+€\s*([\d\.,]+)",
            line,
        )

        if m:
            part = m.group(1)
            description = m.group(2).strip()
            uom = m.group(3)
            quantity = float(m.group(4))
            unit_price = _to_float_eu(m.group(5))
            line_total = _to_float_eu(m.group(6))

            # Append next line if it is continuation (e.g. GRIGIA)
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and "€" not in next_line and not re.match(r"^[A-Z0-9]+", next_line):
                    description += " " + next_line

            results.append({
                "item_no": str(item_no),
                "ship_to": "XX",  # default placeholder
                "customer_product_no": part,
                "te_part_number": part,
                "manufacturer_part_no": part,
                "description": description,
                "quantity": quantity,
                "uom": uom,
                "price": unit_price,
                "line_value": line_total,
                "delivery_date": "",
            })

            item_no += 1

    return results


def parse_boario_impianti(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Boario Impianti S.r.l.",
        "buyer": "",
        "delivery_address": "",
    }

    lines = _extract_lines(text)

    return {"header": header, "lines": lines}