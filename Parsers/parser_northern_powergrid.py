def _extract_lines(text: str):
    lines = text.splitlines()
    results = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Match main item row:
        # 35 163664 Needed: 15 EACH 94 N 1,410.00
        m = re.match(
            r"^(\d+)\s+(\d+)\s+Needed:\s+(\d+)\s+([A-Z]+)\s+([\d,\.]+)\s+[A-Z]\s+([\d,\.]+)",
            line,
        )

        if m:
            item_no = m.group(1)
            part = m.group(2)
            quantity = m.group(3)
            uom = m.group(4)
            unit_price = m.group(5)
            line_total = m.group(6)

            delivery_date = ""
            description_lines = []

            # Next line = delivery date/time
            if i + 1 < len(lines):
                dt_line = lines[i + 1].strip()
                d = re.match(r"^(\d{2}-[A-Z]{3}-\d{4})", dt_line)
                if d:
                    delivery_date = d.group(1)
                    i += 1

            # Collect description lines until next numeric item or "Total:"
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()

                if re.match(r"^\d+\s+\d+", next_line):
                    break
                if next_line.startswith("Total:"):
                    break

                if next_line:
                    description_lines.append(next_line)

                j += 1

            description = " ".join(description_lines).strip()

            results.append({
                "item_no": item_no,
                "customer_product_no": part,
                "description": description,
                "quantity": float(quantity),
                "uom": uom,
                "price": float(unit_price.replace(",", "")),
                "line_value": float(line_total.replace(",", "")),
                "te_part_number": part,
                "manufacturer_part_no": part,
                "delivery_date": delivery_date,
            })

            i = j
            continue

        i += 1

    return results