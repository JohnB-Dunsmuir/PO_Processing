# engine/V12_text_processing.py
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import re

try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
except Exception:  # pragma: no cover
    pdfminer_extract_text = None

try:
    from PyPDF2 import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None


# ============================================================
#  PDF TEXT EXTRACTION (unchanged from V12)
# ============================================================

def extract_text_from_pdf(path: Path, log) -> str:
    """
    Extract text using pdfminer, with PyPDF2 as fallback.
    Mirrors v11.3.2 behaviour.
    """
    txt: Optional[str] = ""
    try:
        if pdfminer_extract_text is not None:
            txt = pdfminer_extract_text(str(path)) or ""
    except Exception as e:
        log.warning("pdfminer failed for %s: %s", path.name, e)

    if (not txt) and PdfReader is not None:
        try:
            reader = PdfReader(str(path))
            txt = "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception as e:
            log.error("PyPDF2 failed for %s: %s", path.name, e)

    return txt or ""


# ============================================================
#  CANONICALISATION HELPERS (NEW IN V12)
# ============================================================

_whitespace_re = re.compile(r"\s+")
_non_alnum_amp_re = re.compile(r"[^0-9A-Z&]+")


def _strip_and_upper(s: Optional[str]) -> str:
    if s is None:
        return ""
    return s.strip().upper()


def normalise_company_name(name: Optional[str]) -> str:
    """
    Canonicalise company names for matching:
    - upper case
    - collapse whitespace
    - simplify punctuation
    - normalise common legal forms (GMBH, CO KG, SRL, SA, etc.)
    """
    s = _strip_and_upper(name)
    if not s:
        return ""

    # Replace common separators with space
    s = s.replace(",", " ")
    s = s.replace(";", " ")
    s = s.replace("/", " ")
    s = s.replace("\\", " ")

    # Normalise ampersand spacing
    s = s.replace("&", " & ")

    # Remove dots – "CO.KG" -> "CO KG", "G.M.B.H." -> "GMBH"
    s = s.replace(".", " ")

    # Collapse whitespace early
    s = _whitespace_re.sub(" ", s)

    # Normalise common legal suffixes
    replacements = {
        " GMBH & CO KG": " GMBH & CO KG",
        " GMBH & CO  KG": " GMBH & CO KG",
        " GMBH & CO   KG": " GMBH & CO KG",
        " GMBH & CO  KG ": " GMBH & CO KG ",
        " GMBH & CO ": " GMBH & CO ",
        " GMBH & CO  ": " GMBH & CO ",
        " GMBH  ": " GMBH ",
        " SRL ": " SRL ",
        " S A ": " SA ",
        " S.A ": " SA ",
        " S A. ": " SA ",
        " SA. ": " SA ",
        " SPA ": " SPA ",
        " S P A ": " SPA ",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)

    # Final whitespace collapse & trim
    s = _whitespace_re.sub(" ", s).strip()

    return s


def normalise_generic_field(value: Optional[str]) -> str:
    """
    Generic normalisation for non-company address fields:
    - upper case
    - collapse whitespace
    - simplify punctuation to spaces
    """
    s = _strip_and_upper(value)
    if not s:
        return ""

    s = s.replace(",", " ")
    s = s.replace(";", " ")
    s = s.replace("/", " ")
    s = s.replace("\\", " ")
    s = s.replace(".", " ")

    s = _whitespace_re.sub(" ", s).strip()
    return s


def canonicalise_address(
    company_name: Optional[str],
    street: Optional[str],
    zip_code: Optional[str],
    city: Optional[str],
    country: Optional[str],
) -> Tuple[str, str, str, str, str]:
    """
    Canonicalise the 5 primary address fields for matching.
    This MUST be used both for:
      - parser output rows
      - master data rows (in memory)
    """
    c_name = normalise_company_name(company_name)
    c_street = normalise_generic_field(street)
    c_zip = normalise_generic_field(zip_code)
    c_city = normalise_generic_field(city)
    c_country = normalise_generic_field(country)

    return c_name, c_street, c_zip, c_city, c_country


def canonical_key_from_fields(
    company_name: Optional[str],
    street: Optional[str],
    zip_code: Optional[str],
    city: Optional[str],
    country: Optional[str],
) -> Tuple[str, str, str, str, str]:
    """
    Produce the canonical key used for Master Data matching:
    (company, street, zip, city, country) after normalisation.
    """
    return canonicalise_address(company_name, street, zip_code, city, country)


def canonical_key_from_row(row: Dict[str, Any]) -> Tuple[str, str, str, str, str]:
    """
    Convenience helper when row is a dict-like structure.
    Expects keys: company_name, street, zip, city, country
    (missing keys are treated as empty strings).
    """
    return canonicalise_address(
        row.get("company_name") or row.get("customer_name"),
        row.get("street"),
        row.get("zip") or row.get("postal_code") or row.get("postcode"),
        row.get("city"),
        row.get("country"),
    )
