# engine/V12_export.py
from datetime import datetime
from pathlib import Path
import shutil

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

DIR_PDFS = BASE_DIR / "01_PDFs"
DIR_PARSED = BASE_DIR / "02_Parsed_Data"
DIR_TODAY = BASE_DIR / "05_Todays_Output"
DIR_HIST = BASE_DIR / "06_Historic_Output_Files"
DIR_ARCHIVE = BASE_DIR / "04_Archive"


def write_full_outputs(df: pd.DataFrame, log):
    DIR_PARSED.mkdir(parents=True, exist_ok=True)
    DIR_TODAY.mkdir(parents=True, exist_ok=True)
    DIR_HIST.mkdir(parents=True, exist_ok=True)

    csv_path = DIR_PARSED / "po_lines_enriched.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    log.info("CSV → %s", csv_path)

    today_path = DIR_TODAY / "Parsed_PO_Lines.xlsx"
    df.to_excel(today_path, index=False)
    log.info("Excel → %s", today_path)

    hist_path = DIR_HIST / f"Parsed_PO_Lines_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
    df.to_excel(hist_path, index=False)
    log.info("Historic → %s", hist_path)


def archive_pdfs(log):
    pdfs = sorted(DIR_PDFS.glob("*.pdf"))
    if not pdfs:
        log.info("No PDFs to archive.")
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    arch_dir = DIR_ARCHIVE / ts / "POs"
    arch_dir.mkdir(parents=True, exist_ok=True)
    for pdf in pdfs:
        shutil.move(str(pdf), arch_dir / pdf.name)
    log.info("Archived all PDFs to %s", arch_dir)
