import re


def detect_led_controls(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "led controls limited" in t and "purchase" in t and "order" in t


def _extract_po_number(text: str) -> str:
    lines = text.splitlines()

    # Look for the line containing ORDER and grab the LAST number on that line or next
    for i, ln in enumerate(lines):
        if "ORDER" in ln.upper():
            window = " ".join(lines[i:i+3])
            nums = re.findall(r"\b\d{5,8}\b", window)
            if nums:
                return nums[-1]  # take the rightmost number
    return ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"\bDate\s+(\d{2}\/\d{2}\/\d{4})\b", text, flags=re.I)
    return m.group(1).replace("/", ".") if m else ""


def _extract_buyer(text: str) -> str:
    # Extract name after the word Contact
    m = re.search(r"Contact\s+.*?\n.*?\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", text, flags=re.S)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    lines = text.splitlines()

    start_idx = None
    for i, ln in enumerate(lines[:40]):
        if ln.strip().lower() == "led controls limited":
            start_idx = i
            break

    if start_idx is not None:
        addr_lines = []
        for j in range(start_idx + 1, min(start_idx + 8, len(lines))):
            s = lines[j].strip()
            if not s:
                continue
            if "ORDER" in s.upper():
                break
            s = s.replace("PURCHASE", "").strip()
            if s:
                addr_lines.append(s)
        if addr_lines:
            return " ".join(addr_lines)

    return "LED Controls Limited, Unit 2 Boran Court, Network 65 Business Park, Hapton, Burnley, BB11 5TH, UK"


def _to_float(num: str) -> float:
    return float(num.replace(",", ""))


def _extract_lines(text: str):
    lines = text.splitlines()
    results = []
    in_table = False
    item_no = 1

    for i in range(len(lines)):
        line = lines[i].strip()

        if line.startswith("Qty Product/Description"):
            in_table = True
            continue

        if not in_table:
            continue

        if line.startswith("Goods Total"):
            break

        # Match beginning of a row
        m = re.match(r"(\d+)\s+EACH\s+([A-Za-z0-9\-\/]+)\s+(.+)", line)

        if m:
            qty = float(m.group(1))
            part = m.group(2)
            rest = m.group(3).split()

            # Find all numeric tokens in the rest
            numeric_tokens = [t for t in rest if re.match(r"^\d+(\.\d+)?$", t)]

            if not numeric_tokens:
                continue

            # First numeric token after part is unit price
            price = float(numeric_tokens[0])

            # Last numeric token is line value
            line_value = float(numeric_tokens[-1])

            description = ""
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not re.match(r"^\d+\s+EACH", next_line):
                    description = next_line

            results.append({
                "item_no": str(item_no),
                "ship_to": "XX",
                "customer_product_no": part,
                "te_part_number": part,
                "manufacturer_part_no": part,
                "description": description,
                "quantity": qty,
                "uom": "EACH",
                "price": price,
                "line_value": line_value,
                "delivery_date": "",
            })

            item_no += 1

    return results


def parse_led_controls(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "LED Controls Limited",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)

    return {"header": header, "lines": lines}