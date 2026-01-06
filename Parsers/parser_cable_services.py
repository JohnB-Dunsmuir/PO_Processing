# Parsers/parser_cable_services.py
"""
parser_cable_services_v16
Cable Services Limited — ROW-GROUP ANCHORED extraction

Fix from v15:
- TE-part scoring was mistakenly choosing measurement/range tokens like "65-95MM"
  (application range) as te_part_number.
- Added a hard filter for range/size tokens ending with MM/MM2 (e.g., 65-95MM, 22-68MM),
  and increased preference for slash-containing TE tokens (e.g., 102L055/S).

Everything else unchanged:
- row-group anchor: Quantity -> EA -> dd/mm/yyyy
- customer_product_no: first "Part No.: XXXXX" in group
- price/ext: "####.#### EA" then next money line
- manufacturer_part_no: SSE if present else TE part
"""

import re
import unicodedata


def detect_cable_services(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return "CABLE SERVICES" in t and "PURCHASE ORDER" in t and "PART NO" in t


def _extract_po_number(text: str) -> str:
    m = re.search(r"Purchase Order Number\s*([0-9]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"\bDate\s*([0-9]{2}/[0-9]{2}/[0-9]{4})\b", text, flags=re.I)
    return m.group(1).replace("/", ".") if m else ""


def _extract_buyer(text: str) -> str:
    m = re.search(r"Buyer Name\s*([A-Za-z ,]+)", text, flags=re.I)
    if not m:
        return ""
    name = m.group(1).strip()
    if "," in name:
        last, first = [p.strip() for p in name.split(",", 1)]
        return f"{first} {last}"
    return name


def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Ship To:\s*([\s\S]*?)Buyer Name", text, flags=re.I)
    if not m:
        return ""
    return " ".join(ln.strip() for ln in m.group(1).splitlines() if ln.strip())


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    for ch in ["\u2010","\u2011","\u2012","\u2013","\u2014","\u2212","\ufe63","\uff0d","\u00ad"]:
        s = s.replace(ch, "-")
    return s


def _clean_lines(text: str):
    return [ln.strip() for ln in _norm(text).splitlines() if ln.strip()]


def _to_float(s: str):
    try:
        return float(str(s).replace(",", "").strip())
    except Exception:
        return None


_DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
_QTY_RE = re.compile(r"^\d{1,6}\.\d{2}$")
_UNIT_PRICE_RE = re.compile(r"(\d+\.\d{4})\s*EA\b", re.I)
_MONEY_2DP_LINE_RE = re.compile(r"^\d[\d,]*\.\d{2}$")
_PARTNO_RE = re.compile(r"Part\s*No\.?\s*[:：]\s*([A-Z0-9\-]+)", re.I)
_SSE_RE = re.compile(r"\bSSE\b\s*[:：]?\s*([A-Z0-9\-]+)\b", re.I)

# New token matchers (v15)
_CODE_TOKEN = re.compile(r"\b[A-Z0-9]+(?:[-/][A-Z0-9]+)+\b")
_CODE_TOKEN_NODASH = re.compile(r"\b[A-Z]{3,6}\d{4,6}\b")  # e.g., SMOE64678

# Filter out application ranges like 65-95MM / 22-68MM etc.
_RANGE_MM_RE = re.compile(r"^\d+(?:-\d+)?MM(?:2)?$", re.I)


def _has_letter_and_digit(tok: str) -> bool:
    return any(c.isalpha() for c in tok) and any(c.isdigit() for c in tok)


def _is_measure_token(tok: str) -> bool:
    return bool(_RANGE_MM_RE.match(tok))


def _score_te(tok: str) -> int:
    t = tok.upper()
    if _is_measure_token(t):
        return -999

    score = 0
    if t.startswith("BAH-") or t.startswith("BAH"):
        score += 10
    if t.startswith("SMOE-") or t.startswith("SMOE"):
        score += 9
    if t.startswith("BSMB"):
        score += 8
    if t.startswith("CRSM"):
        score += 7

    if "-" in t:
        score += 4
    if "/" in t:
        score += 5  # slash is a strong TE hint in this PO

    # small preference for longer tokens (reduces short junk)
    score += min(len(t), 20) // 5  # 0..4
    return score


def _find_rowgroups(lines):
    starts = []
    for i in range(len(lines) - 2):
        q = lines[i]
        if _QTY_RE.match(q) and q != "1.00":
            if lines[i + 1].upper() == "EA" and _DATE_RE.match(lines[i + 2]):
                starts.append((i, _to_float(q), lines[i + 2]))

    groups = []
    for idx, (si, qty, date) in enumerate(starts):
        ei = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        groups.append((si, ei, qty, date))
    return groups


def _extract_from_group(seg_lines):
    customer_part = ""
    for ln in seg_lines:
        m = _PARTNO_RE.search(ln)
        if m:
            customer_part = m.group(1).strip()
            break

    unit_price = None
    ext_price = None
    unit_idx = None
    for j, ln in enumerate(seg_lines):
        m = _UNIT_PRICE_RE.search(ln)
        if m:
            unit_price = _to_float(m.group(1))
            unit_idx = j
            break
    if unit_idx is not None:
        for j2 in range(unit_idx + 1, len(seg_lines)):
            if _MONEY_2DP_LINE_RE.match(seg_lines[j2]):
                ext_price = _to_float(seg_lines[j2])
                break

    sse = ""
    for ln in seg_lines:
        m = _SSE_RE.search(ln)
        if m:
            sse = m.group(1).strip()
            break

    te_part = ""
    best = ("", -1)
    search_zone = seg_lines[: min(len(seg_lines), 35)]
    cust_u = customer_part.upper() if customer_part else ""

    for ln in search_zone:
        u = ln.upper()

        for tok in _CODE_TOKEN.findall(u):
            if cust_u and tok == cust_u:
                continue
            if not _has_letter_and_digit(tok):
                continue
            sc = _score_te(tok)
            if sc > best[1]:
                best = (tok, sc)

        for tok in _CODE_TOKEN_NODASH.findall(u):
            if cust_u and tok == cust_u:
                continue
            sc = _score_te(tok)
            if sc > best[1]:
                best = (tok, sc)

    te_part = best[0]

    if te_part and _CODE_TOKEN_NODASH.fullmatch(te_part):
        dashed = re.sub(r"^([A-Z]{3,6})(\d+)$", r"\1-\2", te_part)
        if any(dashed in ln.upper() for ln in seg_lines):
            te_part = dashed

    manufacturer_part = sse or te_part
    return customer_part, te_part, manufacturer_part, unit_price, ext_price


def _extract_lines(text: str):
    lines = _clean_lines(text)
    groups = _find_rowgroups(lines)
    out = []

    for idx, (si, ei, qty, date) in enumerate(groups, start=1):
        seg = lines[si:ei]
        customer_part, te_part, mfg_part, unit_price, ext_price = _extract_from_group(seg)

        out.append({
            "item_no": str(idx),
            "customer_product_no": customer_part,
            "description": "",
            "quantity": qty if qty is not None else "",
            "uom": "EA",
            "price": unit_price if unit_price is not None else "",
            "line_value": ext_price if ext_price is not None else "",
            "te_part_number": te_part,
            "manufacturer_part_no": mfg_part,
            "delivery_date": date.replace("/", "."),
        })

    return out


def parse_cable_services(text: str) -> dict:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Cable Services Limited",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)
    if not lines:
        raise ValueError("Cable Services parser: no line items extracted")

    return {"header": header, "lines": lines}
