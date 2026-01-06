# Parsers/parser_sre.py
# Parser for SRE (Synergie Réseaux Électricité) Purchase Orders
# Works with unified process_purchase_orders.py
# Detects SRE POs and emits standardized RPA output

import re
import os

def detect_sre(text: str) -> bool:
    """
    Triggers on:
      - 'SRE' logo/header or 'Synergie Réseaux Électricité'
      - French layout with 'Commande' + SRE/...
      - 'Adresse de livraison' block
    """
    t = (text or "").upper()
    return any([
        "SYNERGIE RÉSEAUX ÉLECTRICITÉ" in t or "SYNERGIE RESEAUX ELECTRICITE" in t,
        "COMMANDE" in t and "SRE/" in t,
        "ADRESSE DE LIVRAISON" in t,
        "MICHAUD LOGISTIQUE" in t
    ])


def parse_sre(text: str, source_file: str = "") -> list:
    """
    Extracts SRE PO data into the unified RPA schema (TLA Distribution headers).
    Returns one dict per PO line. All missing fields -> "" for standing-data merge.
    """
    source_name = os.path.basename(source_file)

    # ---------- HEADER ----------
    # e.g., "Commande\nSRE/F00876\n25/06/2025"
    po_number = _search(r"Commande\s+([A-Z]{3}/[A-Z0-9]+)", text)
    po_date   = _search(r"Commande\s+[A-Z]{3}/[A-Z0-9]+\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text) \
                or _search(r"([0-9]{2}/[0-9]{2}/[0-9]{4})", text)  # fallback
    buyer     = _search(r"Acheteur\s*([\wÉÈÀÂÎÔÛéèàâîôû' \-]+)", text) \
                or _search(r"COLLAUDIN\s*Emmanuel", text, return_literal=True) or "COLLAUDIN Emmanuel"

    # Delivery address block on page 1
    delivery_address = _extract_delivery_address(text)

    # ---------- LINE ITEMS ----------
    # Table rows pattern (page 1):
    # [2107259-1] ECAU240115 - TROUSSE ...
    # TYC2107259-1 5,000 U 30/06/2025 45,300 226,50 €
    line_pat = re.compile(
        r"\[(?P<mfg>[A-Z0-9\-]+)\][^\n]*?\n"
        r"(?P<te>TYC[A-Z0-9\-]+)\s+"
        r"(?P<qty>[\d\.,]+)\s+"
        r"(?P<uom>[A-Z])\s+"
        r"(?P<date>\d{2}/\d{2}/\d{4})\s+"
        r"(?P<price>[\d\.,]+)\s+"
        r"(?P<total>[\d\.,]+\s*€?)",
        re.IGNORECASE
    )

    results = []
    item_index = 0
    for match in line_pat.finditer(text):
        item_index += 1
        # Description line is the bracketed line itself minus the leading [code]
        desc_line = _extract_bracket_desc_before(match, text)
        results.append({
            "Purchase Order": po_number or "",
            "Date on PO": po_date or "",
            "Source.Name": source_name,
            "Quantity": match.group("qty"),
            "UoM": match.group("uom"),
            "Customer Product number": match.group("mfg"),             # customer’s bracket code
            "Description": desc_line,
            "TE Product No.": match.group("te"),
            "Manufacturer's Part No.": "",                             # not explicitly present
            "Delivery Date": match.group("date"),
            "Currency": "EUR",
            "Net Price": match.group("price"),
            "Total Net Value": _strip_euro(match.group("total")),
            "Item Number": str(item_index).zfill(3),
            "Distribution Channel": "",
            "Sales Org": "",
            "Bl": "",
            "Ship to ID": "",
            "Sold to Number": "",
            "Order Type": "Standard",
            "Buyer": buyer or "",
            "Delivery Address": delivery_address,
            "Relevant dummy part number": ""
        })

    return results


# -------------------- helpers --------------------

def _search(pattern: str, text: str, return_literal: bool = False) -> str:
    if return_literal:
        return pattern if (pattern and (pattern in text)) else ""
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def _strip_euro(s: str) -> str:
    return re.sub(r"\s*€", "", (s or "").strip())

def _extract_delivery_address(text: str) -> str:
    """
    Extracts the 'Adresse de livraison' block into one line.
    Example (page 1):
    MICHAUD LOGISTIQUE, ZAC ECOSPHERE, 428 RUE DE LA BATIE, 01160 PONT D’AIN, France
    """
    m = re.search(r"Adresse de livraison\s*([\s\S]*?)Adresse du fournisseur", text, re.IGNORECASE)
    if not m:
        return ""
    block = m.group(1)
    # take first 4-6 lines (company + street + city/postcode + country)
    lines = [ln.strip() for ln in block.strip().splitlines() if ln.strip()]
    # limit noise
    lines = lines[:6]
    return ", ".join(lines)

def _extract_bracket_desc_before(match: re.Match, text: str) -> str:
    """
    The human-readable description is on the bracket line,
    e.g. "[2107259-1] ECAU240115 - TROUSSE TUR NOUVEAU CABLE 6982015"
    We return that line without the leading [code].
    """
    span_start = text.rfind("\n", 0, match.start())
    line_start = span_start + 1 if span_start != -1 else 0
    line = text[line_start: match.start()].strip()
    # drop the bracketed code itself
    line = re.sub(r"^\[[A-Z0-9\-]+\]\s*", "", line).strip()
    # condense whitespace
    return re.sub(r"\s{2,}", " ", line)


def detect_sre(text: str) -> bool:
    # Detects Sre purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "SRE" in t,                 # company name
        "@SRE.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
