# diagnose_one_pdf.py
# Run a single-PDF diagnostic using the same Parsers/ modules your V12 pipeline uses.
# Does NOT modify Streamlit or V12_main.

import os
import sys
import importlib
from pathlib import Path
from typing import Dict, Any, List, Tuple

try:
    import pdfplumber
except ImportError:
    print("[ERROR] pdfplumber is not installed. Install it in your venv.")
    sys.exit(2)


REQUIRED_HEADER_KEYS = [
    "po_number",
    "po_date",
    "customer_name",
    "buyer",
    "delivery_address",
]


def read_pdf_text(pdf_path: Path) -> str:
    text_parts: List[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            if t.strip():
                text_parts.append(t)
    return "\n".join(text_parts)


def load_parsers(parsers_dir: Path) -> List[Tuple[str, Any]]:
    """
    Loads Parsers/parser_*.py modules and returns list of:
      (module_name, module_object)
    """
    sys.path.insert(0, str(parsers_dir.parent))  # so "Parsers" is importable
    modules = []
    for py in sorted(parsers_dir.glob("parser_*.py")):
        mod_name = f"Parsers.{py.stem}"
        try:
            mod = importlib.import_module(mod_name)
            modules.append((mod_name, mod))
        except Exception as e:
            print(f"[WARN] Failed to import {mod_name}: {e}")
    return modules


def find_parser(modules: List[Tuple[str, Any]], text: str) -> Tuple[str, Any]:
    """
    Finds first parser whose detect_* returns True.
    """
    for mod_name, mod in modules:
        detect_fns = [getattr(mod, fn) for fn in dir(mod) if fn.startswith("detect_")]
        parse_fns = [getattr(mod, fn) for fn in dir(mod) if fn.startswith("parse_")]

        if not detect_fns or not parse_fns:
            continue

        # Prefer matching detect_* and parse_* with same suffix, else fallback to first parse_*
        for det in detect_fns:
            try:
                if det(text):
                    det_suffix = det.__name__.replace("detect_", "")
                    parse = getattr(mod, f"parse_{det_suffix}", None)
                    if callable(parse):
                        return mod_name, parse
                    # fallback
                    return mod_name, parse_fns[0]
            except Exception:
                continue

    return "NONE", None


def normalize(v: Any) -> str:
    if v is None:
        return "Not found"
    s = str(v).strip()
    return s if s else "Not found"


def main():
    if len(sys.argv) < 2:
        print("Usage: python diagnose_one_pdf.py <path_to_pdf>")
        sys.exit(2)

    pdf_path = Path(sys.argv[1]).expanduser().resolve()
    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}")
        sys.exit(2)

    repo_root = Path(__file__).resolve().parent
    parsers_dir = repo_root / "Parsers"
    if not parsers_dir.exists():
        print(f"[ERROR] Parsers directory not found at: {parsers_dir}")
        sys.exit(2)

    print(f"[INFO] PDF: {pdf_path.name}")
    text = read_pdf_text(pdf_path)
    print(f"[INFO] Extracted chars: {len(text)}")
    safe_head = repr(text[:200]).encode("utf-8", "backslashreplace").decode("utf-8", "ignore")
    print(f"[INFO] Text head(200): {safe_head}")


    modules = load_parsers(parsers_dir)
    print(f"[INFO] Loaded parser modules: {len(modules)}")

    mod_name, parse_fn = find_parser(modules, text)
    if parse_fn is None:
        print("[FAIL] No parser detected this PDF.")
        sys.exit(1)

    print(f"[INFO] Detected parser module: {mod_name}")
    try:
        result: Dict[str, Any] = parse_fn(text)
    except Exception as e:
        print(f"[FAIL] Parser crashed during parse(): {e}")
        sys.exit(1)

    header = result.get("header") or {}
    lines = result.get("lines") or []

    print("\n=== HEADER CHECK ===")
    missing = []
    for k in REQUIRED_HEADER_KEYS:
        val = normalize(header.get(k))
        ok = val != "Not found"
        print(f"- {k}: {val} {'OK' if ok else 'MISSING'}")
        if not ok:
            missing.append(k)

    print("\n=== LINES CHECK ===")
    print(f"- lines_count: {len(lines)}")
    if len(lines) > 0:
        print("- first_line:", lines[0])
        if len(lines) > 1:
            print("- second_line:", lines[1])

    # Exit code rules: fail if no lines OR missing required header keys
    if missing or len(lines) == 0:
        print("\n[FAIL] Contract not met:")
        if missing:
            print(f"  - Missing header fields: {', '.join(missing)}")
        if len(lines) == 0:
            print("  - No line items produced")
        sys.exit(1)

    print("\n[PASS] Parser output looks Extractor-safe.")
    sys.exit(0)


if __name__ == "__main__":
    main()
