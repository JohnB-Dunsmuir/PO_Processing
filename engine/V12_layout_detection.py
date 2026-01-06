# engine/V12_layout_detection.py
import hashlib
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional

import re


@dataclass
class LayoutSignature:
    customer: str
    signature_hash: str
    raw_signature: Dict[str, Any]


def _build_layout_signature_struct(text: str) -> Dict[str, Any]:
    """
    Very lightweight structural signature of a PO:
    - line pattern counts
    - presence of key header anchors
    - numeric / text ratios, etc.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    header_markers = [
        "PURCHASE ORDER",
        "BESTELLNUMMER",
        "ORDER NR",
        "PO NUMBER",
        "LIEFERADRESSE",
        "DELIVERY ADDRESS",
        "SHIP TO",
        "RECHNUNGSANSCHRIFT",
        "INVOICE ADDRESS",
    ]

    present_headers = [
        h for h in header_markers if any(h in ln.upper() for ln in lines)
    ]

    # crude stats
    total_lines = len(lines)
    digit_lines = sum(1 for ln in lines if re.search(r"\d", ln))
    table_like = sum(1 for ln in lines if re.search(r"\d+\s+\S+\s+\d", ln))

    sig = {
        "total_lines": total_lines,
        "digit_lines": digit_lines,
        "table_like_lines": table_like,
        "header_markers": sorted(present_headers),
    }
    return sig


def compute_layout_signature(customer_name: str, text: str) -> LayoutSignature:
    sig_struct = _build_layout_signature_struct(text)
    sig_bytes = json.dumps(sig_struct, sort_keys=True).encode("utf-8")
    h = hashlib.sha256(sig_bytes).hexdigest()
    return LayoutSignature(customer=customer_name, signature_hash=h, raw_signature=sig_struct)


def compare_signatures(
    old: LayoutSignature, new: LayoutSignature
) -> float:
    """
    Very rough similarity metric in [0,1].
    1.0 = identical hash, 0.0 = structurally very different.
    For now, we just check hash equality → 1.0 or 0.0.
    You can extend this later if you log multiple signatures.
    """
    return 1.0 if old.signature_hash == new.signature_hash else 0.0


class LayoutRegistry:
    """
    In-memory registry for this run.
    In future you could persist to disk for cross-run learning.
    """

    def __init__(self):
        self.by_customer: Dict[str, LayoutSignature] = {}

    def check_and_log(self, customer: str, text: str, log, threshold: float = 0.8):
        sig = compute_layout_signature(customer, text)
        old: Optional[LayoutSignature] = self.by_customer.get(customer)
        if old is None:
            self.by_customer[customer] = sig
            return

        sim = compare_signatures(old, sig)
        if sim < threshold:
            log.warning(
                "Layout change detected for customer '%s' (similarity %.2f). "
                "This may indicate a new PO format.",
                customer,
                sim,
            )
            log.debug("Old layout signature: %s", old.raw_signature)
            log.debug("New layout signature: %s", sig.raw_signature)

        # update to latest
        self.by_customer[customer] = sig
