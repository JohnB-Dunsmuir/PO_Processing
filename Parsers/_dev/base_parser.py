import re
import pdfplumber

def norm_space(s: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", s or "").strip()

def read_text(path: str) -> str:
    """Read all text from a PDF (page by page)."""
    out = []
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            out.append(p.extract_text() or "")
    return "\n".join(out)

# ---------- Heuristic header extractors (safe fallbacks) ----------
DTE = r"(?:\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4})"

def guess_po_number(text: str) -> str:
    m = re.search(r"(?:PO\s*Number|Purchase\s*Order|Order\s*No\.?|Order\s*Ref)\s*[:#]?\s*([A-Za-z0-9\-\/]+)", text, re.I)
    return norm_space(m.group(1)) if m else "Not found"

def guess_po_date(text: str) -> str:
    m = re.search(r"(?:PO\s*Date|Order\s*Date|Date)\s*[:]?\s*(" + DTE + ")", text, re.I)
    return norm_space(m.group(1)) if m else "Not found"

def guess_buyer(text: str) -> str:
    m = re.search(r"(?:Buyer|Taken\s*By|Ordered\s*By)\s*[:]?\s*([A-Za-z ,.'-]{3,})", text, re.I)
    return norm_space(m.group(1)) if m else "Not found"

def guess_delivery_address(text: str) -> str:
    """
    Look for a block following 'Delivery Address' / 'Deliver To'.
    Falls back to UK-postcode-style block if found.
    """
    # Primary: labeled block
    m = re.search(r"(?:Delivery\s*Address|Deliver\s*To)\s*:?\s*(.+?)(?:\n\s*\n|$)", text, re.I | re.S)
    if m:
        block = m.group(1)
        lines = [l.strip() for l in block.splitlines() if l.strip()][:8]
        return norm_space(", ".join(lines))

    # Fallback: UK postcode pattern – include ~5 lines around it
    m = re.search(r"\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})\b", text)
    if m:
        lines = text.splitlines()
        idx = next((i for i, l in enumerate(lines) if m.group(1) in l), None)
        if idx is not None:
            start = max(0, idx - 6)
            end = min(len(lines), idx + 1)
            return norm_space(", ".join(l.strip() for l in lines[start:end] if l.strip()))

    return "Not found"

def detect_customer_name(text: str) -> str:
    """
    Try to pick a plausible customer name line near the top,
    skipping common boilerplate words.
    """
    skip = re.compile(r"(purchase order|order|invoice|bill to|ship to|deliver to|delivery address)", re.I)
    for line in text.splitlines()[:20]:
        ls = line.strip()
        if len(ls) > 6 and not skip.search(ls):
            return norm_space(ls)
    return "Not found"
