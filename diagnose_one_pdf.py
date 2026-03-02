# diagnose_one_pdf.py
# Single-PDF diagnostic + callable wrapper
# CLI behaviour preserved

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
    parts: List[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            if t.strip():
                parts.append(t)
    return "\n".join(parts)


def load_parsers(parsers_dir: Path) -> List[Tuple[str, Any]]:
    sys.path.insert(0, str(parsers_dir.parent))
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
    for mod_name, mod in modules:
        detect_fns = [getattr(mod, fn) for fn in dir(mod) if fn.startswith("detect_")]
        parse_fns = [getattr(mod, fn) for fn in dir(mod) if fn.startswith("parse_")]

        if not detect_fns or not parse_fns:
            continue

        for det in detect_fns:
            try:
                if det(text):
                    suffix = det.__name__.replace("detect_", "")
                    parse = getattr(mod, f"parse_{suffix}", None)
                    return mod_name, parse or parse_fns[0]
            except Exception:
                continue

    return "NONE", None


def normalize(v: Any) -> str:
    if v is None:
        return "Not found"
    s = str(v).strip()
    return s if s else "Not found"


# ------------------------------------------------------------------
# CALLABLE WRAPPER (FOR STREAMLIT / WRAPPER_STDOUT)
# ------------------------------------------------------------------

def diagnose_one_pdf_wrapper(
    pdf_path: str,
    forced_parser: str | None = None,
    stdout: bool = True,
) -> Dict[str, Any]:

    pdf_path = Path(pdf_path).expanduser().resolve()
    repo_root = Path(__file__).resolve().parent
    parsers_dir = repo_root / "Parsers"

    text = read_pdf_text(pdf_path)
    extracted_chars = len(text)

    modules = load_parsers(parsers_dir)

    # ---------------------------
    # Forced parser selection (FIXED)
    # ---------------------------
    if forced_parser:
        parse_fn = None
        mod_name = None

        # forced_parser should be the module stem, e.g. "parser_northern_powergrid"
        forced_norm = str(forced_parser).strip().lower()

        for name, mod in modules:
            module_short_name = name.split(".")[-1].strip().lower()  # e.g. parser_northern_powergrid

            if module_short_name == forced_norm:
                parse_fns = [getattr(mod, fn) for fn in dir(mod) if fn.startswith("parse_")]
                parse_fn = parse_fns[0] if parse_fns else None
                mod_name = name
                break

        if parse_fn is None:
            raise RuntimeError(f"Forced parser '{forced_parser}' not found.")
    else:
        mod_name, parse_fn = find_parser(modules, text)

    if parse_fn is None:
        raise RuntimeError("No parser detected")

    result = parse_fn(text) or {}
    header = result.get("header") or {}
    lines = result.get("lines") or []

    if stdout:
        print(f"[INFO] PDF: {pdf_path.name}")
        print(f"[INFO] Extracted chars: {extracted_chars}")
        print(f"[INFO] Detected parser module: {mod_name}")

        print("\n=== HEADER CHECK ===")
        for k in REQUIRED_HEADER_KEYS:
            val = normalize(header.get(k))
            print(f"- {k}: {val}")

        print("\n=== LINES CHECK ===")
        print(f"- lines_count: {len(lines)}")
        if lines:
            print("- first_line:", lines[0])
            if len(lines) > 1:
                print("- second_line:", lines[1])

        print("\n[PASS] Parser output looks Extractor-safe.")

    return {
        "detected_parser": mod_name,
        "extracted_chars": extracted_chars,
        "header": header,
        "lines": lines,
    }


# ------------------------------------------------------------------
# CLI ENTRY POINT (UNCHANGED BEHAVIOUR)
# ------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python diagnose_one_pdf.py <path_to_pdf>")
        sys.exit(2)

    pdf_path = Path(sys.argv[1]).expanduser().resolve()
    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}")
        sys.exit(2)

    result = diagnose_one_pdf_wrapper(str(pdf_path), stdout=True)

    missing = [
        k for k in REQUIRED_HEADER_KEYS
        if normalize(result["header"].get(k)) == "Not found"
    ]

    if missing or not result["lines"]:
        print("\n[FAIL] Contract not met:")
        if missing:
            print(f"  - Missing header fields: {', '.join(missing)}")
        if not result["lines"]:
            print("  - No line items produced")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()