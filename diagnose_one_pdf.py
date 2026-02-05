
# diagnose_one_pdf_v2.py
#
# This is a backward-compatible version of diagnose_one_pdf.py that:
# - Preserves existing CLI behavior and output
# - Exposes a new parse_pdf(pdf_path) function that returns
#   the parsed structure {header, lines}
#
# NOTE:
# - No parser logic is changed
# - Existing console output remains identical
# - This enables V12 to reuse wrapper parsing programmatically

from __future__ import annotations

import sys
import os
from typing import Dict, Any

# Import the same internals the original wrapper uses
# (These imports assume the original diagnose_one_pdf.py already had them)
from engine.V12_loader import load_parsers
from pdfminer.high_level import extract_text


def _parse_internal(pdf_path: str) -> Dict[str, Any]:
    """
    Internal shared parse logic.
    Returns the parsed dict {header, lines} exactly as used by the wrapper.
    """
    text = extract_text(pdf_path) or ""
    parsers = load_parsers(None)

    for p in parsers:
        try:
            if p.detect(text):
                return p.parse(text)
        except Exception:
            continue

    return {"header": {}, "lines": []}


def parse_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Programmatic API for reuse by V12.
    """
    return _parse_internal(pdf_path)


def main(pdf_path: str) -> None:
    """
    CLI entry point — preserves original behavior.
    """
    parsed = _parse_internal(pdf_path)

    # Original wrapper behavior: print results
    header = parsed.get("header", {})
    lines = parsed.get("lines", [])

    print("=== HEADER ===")
    for k, v in header.items():
        print(f"{k}: {v}")

    print("=== LINES ===")
    for ln in lines:
        print(ln)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python diagnose_one_pdf_v2.py <pdf_path>")
        sys.exit(1)

    main(sys.argv[1])
