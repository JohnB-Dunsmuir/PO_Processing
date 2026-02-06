# streamlit_app.py
# FINAL – Ship to (or Ship to ID) authoritative for parser + extractor

from __future__ import annotations
import re
import shutil
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd

from run_v12_wrapper_stdout import run_v12_wrapper_stdout
from build_extractor_output import build_extractor_output

BASE = Path(__file__).resolve().parent
DIR_PDFS = BASE / "01_PDFs"
DIR_PARSED = BASE / "02_Parsed_Data"
DIR_ARCHIVE = BASE / "04_Archive"

MASTER_PATH = BASE / "03_Master_Data" / "Master Data.xlsx"
PARSED_XLSX = BASE / "Parsed_PO_Lines.xlsx"
OUT_XLSX = DIR_PARSED / "Extractor_Output.xlsx"
OUT_CSV = DIR_PARSED / "Extractor_Output.csv"
FORCED_CSV = DIR_PARSED / "forced_parsers.csv"

SHIP_TO_PATTERNS = [
    re.compile(r"^\d{8}$"),
    re.compile(r"^\d{10}\*D$"),
]

def pick_col_ci(df: pd.DataFrame, *candidates: str) -> str:
    for cand in candidates:
        for c in df.columns:
            if c.strip().lower() == cand.strip().lower():
                return c
    raise KeyError(f"None of columns found: {candidates}")

@st.cache_data
def load_master():
    return pd.read_excel(MASTER_PATH, dtype=str).fillna("")

def backup_existing_pdfs():
    DIR_PDFS.mkdir(exist_ok=True)
    DIR_ARCHIVE.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = DIR_ARCHIVE / f"backup_{ts}"
    dest.mkdir()
    for p in DIR_PDFS.glob("*.pdf"):
        shutil.move(str(p), dest / p.name)

def write_uploaded_pdfs(files):
    DIR_PDFS.mkdir(exist_ok=True)
    for f in files:
        (DIR_PDFS / f.name).write_bytes(f.getbuffer())

st.set_page_config(layout="wide")
st.title("PO Processing – Ship-to Controlled")

df_master = load_master()

# Resolve Master columns ONCE
SHIP_TO_COL = pick_col_ci(df_master, "Ship to ID", "Ship to")
PARSER_COL = pick_col_ci(df_master, "Parser Used")

uploaded = st.file_uploader("Upload PO PDFs", type=["pdf"], accept_multiple_files=True)

rows = []
errors = []

if uploaded:
    st.subheader("Ship to per PDF")

    for f in uploaded:
        ship_to = st.text_input(f"{f.name} – Ship to").strip()

        if not any(p.match(ship_to) for p in SHIP_TO_PATTERNS):
            errors.append(f.name)
            st.error("Invalid Ship to format")
            continue

        m = df_master[df_master[SHIP_TO_COL] == ship_to]
        if m.empty:
            errors.append(f.name)
            st.error("Ship to not found in Master Data")
            continue

        parser_used = m.iloc[0][PARSER_COL]

        rows.append({
            "SourceFile": f.name,
            "Ship to ID": ship_to,
            "Parser Used": parser_used,
        })

        st.success(f"OK → {parser_used}")

run = st.button("Run", disabled=bool(errors) or not uploaded)

if run:
    backup_existing_pdfs()
    write_uploaded_pdfs(uploaded)
    DIR_PARSED.mkdir(exist_ok=True)

    # Persist Ship to + parser mapping
    pd.DataFrame(rows).to_csv(FORCED_CSV, index=False)

    parsed_rows = []

    for r in rows:
        pdf = DIR_PDFS / r["SourceFile"]

        result = run_v12_wrapper_stdout(
            pdf_path=str(pdf),
            parser_override=r["Parser Used"],  # authoritative
            stdout=True,
        )

        for line in result["lines"]:
            parsed_rows.append({
                "SourceFile": pdf.name,
                **result["header"],
                **line,
            })

    pd.DataFrame(parsed_rows).to_excel(PARSED_XLSX, index=False)

    build_extractor_output(
        parsed_path=PARSED_XLSX,
        master_path=MASTER_PATH,
        out_xlsx=OUT_XLSX,
        out_csv=OUT_CSV,
        csv_sep=";",
        unit_default=1,
    )

    st.success("Extraction complete")

st.subheader("Downloads")

for label, path, mime in [
    ("Parsed_PO_Lines.xlsx", PARSED_XLSX, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ("Extractor_Output.xlsx", OUT_XLSX, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ("Extractor_Output.csv", OUT_CSV, "text/csv"),
]:
    if path.exists():
        st.download_button(label, path.read_bytes(), label, mime)