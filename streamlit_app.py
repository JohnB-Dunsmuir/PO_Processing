# streamlit_app.py
# Robust Streamlit front-end for PO_Processing V12 (Windows/OneDrive-safe)
#
# What this version fixes:
# - Never crashes if OneDrive races (files disappear between glob/copy)
# - Never crashes if Excel locks output files (safe temp copies for download)
# - Minimal logic: upload PDFs -> run engine -> build Extractor output -> download
#
# Requirements:
# - engine.V12_parser_engine.process_all_pdfs
# - build_extractor_output.build_extractor_output
# - Master Data at ./03_Master_Data/Master Data.xlsx

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
import streamlit as st
import pandas as pd

from engine.V12_parser_engine import process_all_pdfs
from build_extractor_output import build_extractor_output

BASE = Path(__file__).resolve().parent
DIR_PDFS = BASE / "01_PDFs"
DIR_ARCHIVE = BASE / "04_Archive"
DIR_PARSED = BASE / "02_Parsed_Data"
DIR_TEMP = BASE / "00_Temp_Downloads"

MASTER_PATH = BASE / "03_Master_Data" / "Master Data.xlsx"
PARSED_XLSX = BASE / "Parsed_PO_Lines.xlsx"
OUT_XLSX = DIR_PARSED / "Extractor_Output.xlsx"
OUT_CSV = DIR_PARSED / "Extractor_Output.csv"


def backup_existing_pdfs() -> None:
    """Move existing PDFs out of 01_PDFs without ever crashing (OneDrive-safe)."""
    DIR_PDFS.mkdir(parents=True, exist_ok=True)
    DIR_ARCHIVE.mkdir(parents=True, exist_ok=True)

    pdfs = list(DIR_PDFS.glob("*.pdf")) + list(DIR_PDFS.glob("*.PDF"))
    if not pdfs:
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = DIR_ARCHIVE / f"streamlit_backup_{ts}"
    dest.mkdir(parents=True, exist_ok=True)

    for p in pdfs:
        try:
            if not p.exists():
                continue
            try:
                shutil.move(str(p), str(dest / p.name))
            except Exception:
                # fallback copy
                try:
                    shutil.copy2(str(p), str(dest / p.name))
                    try:
                        p.unlink()
                    except Exception:
                        pass
                except Exception:
                    continue
        except Exception:
            continue


def write_uploaded_pdfs(uploaded_files) -> None:
    DIR_PDFS.mkdir(parents=True, exist_ok=True)
    for f in uploaded_files:
        try:
            (DIR_PDFS / f.name).write_bytes(f.getbuffer())
        except Exception:
            continue


def file_bytes_safe(path: Path) -> bytes:
    """Read bytes even if Excel/OneDrive locks the file."""
    try:
        return path.read_bytes()
    except Exception:
        DIR_TEMP.mkdir(parents=True, exist_ok=True)
        tmp = DIR_TEMP / f"{path.stem}_download{path.suffix}"
        try:
            shutil.copy2(path, tmp)
            return tmp.read_bytes()
        except Exception:
            return b""


# ---------------- Streamlit UI ----------------

st.set_page_config(page_title="PO Processing (V12)", layout="wide")
st.title("PO Processing (V12) — SAP Extractor")

st.caption(
    "Upload PO PDFs, run parsers, and download SAP-ready Extractor output "
    "(TE standing data applied)."
)

with st.sidebar:
    st.header("Status")
    st.write(f"Master Data: `{MASTER_PATH.relative_to(BASE)}`")
    st.write("Master Data found ✅" if MASTER_PATH.exists() else "Master Data missing ❌")
    st.write(f"PDF folder: `{DIR_PDFS.relative_to(BASE)}`")
    st.write(f"Output: `{OUT_XLSX.relative_to(BASE)}`")

st.subheader("1) Upload PDFs")
uploaded = st.file_uploader(
    "Select one or more PO PDFs",
    type=["pdf", "PDF"],
    accept_multiple_files=True,
)

run = st.button(
    "Run parsers + build Extractor output",
    type="primary",
    disabled=(not uploaded or not MASTER_PATH.exists()),
)

if run:
    st.info("Preparing input folder...")
    backup_existing_pdfs()
    write_uploaded_pdfs(uploaded)

    st.info("Running parser engine...")
    process_all_pdfs()

    if not PARSED_XLSX.exists():
        st.error("Parsed_PO_Lines.xlsx was not created. Check logs.")
    else:
        st.success("Parsed output created.")

    st.info("Building SAP Extractor output...")
    try:
        build_extractor_output(
            parsed_path=PARSED_XLSX,
            master_path=MASTER_PATH,
            out_xlsx=OUT_XLSX,
            out_csv=OUT_CSV,
            csv_sep=";",
            unit_default=1,
        )
        st.success("Extractor output created.")
    except Exception as e:
        st.exception(e)

st.subheader("2) Download outputs")

c1, c2, c3 = st.columns(3)

with c1:
    if PARSED_XLSX.exists():
        st.download_button(
            "Download Parsed_PO_Lines.xlsx",
            data=file_bytes_safe(PARSED_XLSX),
            file_name=PARSED_XLSX.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.write("Parsed output not present.")

with c2:
    if OUT_XLSX.exists():
        st.download_button(
            "Download Extractor_Output.xlsx",
            data=file_bytes_safe(OUT_XLSX),
            file_name=OUT_XLSX.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.write("Extractor output not present.")

with c3:
    if OUT_CSV.exists():
        st.download_button(
            "Download Extractor_Output.csv",
            data=file_bytes_safe(OUT_CSV),
            file_name=OUT_CSV.name,
            mime="text/csv",
        )
    else:
        st.write("Extractor CSV not present.")

st.subheader("3) Preview")
if OUT_XLSX.exists():
    try:
        df_prev = pd.read_excel(OUT_XLSX, dtype=str).fillna("")
        st.dataframe(df_prev.head(50), use_container_width=True)
    except Exception as e:
        st.warning(f"Preview failed: {e}")
