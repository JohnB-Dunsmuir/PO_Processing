# Parsers/ocr_helper.py
# OCR via Poppler (pdftoppm) + Tesseract CLI (no pytesseract needed)

import os
import shutil
import subprocess
import tempfile

def _which(cmd: str):
    from shutil import which
    return which(cmd)

def _require_tool(cmd: str, friendly: str):
    if not _which(cmd):
        raise RuntimeError(
            f"Missing dependency: '{cmd}' not found on PATH. "
            f"Please install {friendly} and ensure its bin folder is on PATH."
        )

def extract_text_ocr(pdf_path: str, dpi: int = 300, lang: str = "deu+eng") -> str:
    """
    Convert PDF pages to PNG with pdftoppm, run Tesseract OCR on each, return concatenated text.
    Requires:
      - Poppler (pdftoppm)   → winget install oschwartz10612.Poppler
      - Tesseract (tesseract)→ winget install UB-Mannheim.TesseractOCR
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(pdf_path)

    _require_tool("pdftoppm", "Poppler (oschwartz10612.Poppler)")
    _require_tool("tesseract", "Tesseract OCR (UB-Mannheim.TesseractOCR)")

    tmpdir = tempfile.mkdtemp(prefix="ocr_")
    try:
        # 1) PDF → PNG pages
        png_prefix = os.path.join(tmpdir, "page")
        cmd_ppm = ["pdftoppm", "-png", "-r", str(dpi), pdf_path, png_prefix]
        subprocess.run(cmd_ppm, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        images = sorted(
            [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.lower().endswith(".png")],
            key=lambda p: p.lower()
        )
        if not images:
            return ""

        # 2) OCR each page with Tesseract → stdout
        full_text_parts = []
        for i, img_path in enumerate(images, 1):
            print(f"🧠 OCR (tesseract) page {i}/{len(images)} …")
            cmd_ocr = ["tesseract", img_path, "stdout", "-l", lang]
            proc = subprocess.run(cmd_ocr, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            text = proc.stdout.decode("utf-8", errors="ignore")
            full_text_parts.append(text)

        return "\n".join(full_text_parts)

    finally:
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass
