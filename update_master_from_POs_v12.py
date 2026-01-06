# update_master_from_POs_v12.py
# ============================================================
# V12 Master Data Update Script
# - Merges consultant-filled Unmatched_Addresses.xlsx into Master Data
# - Writes a NEW clean master to prove schema + matching works
# - Clears unmatched rows after successful merge (preserves columns)
# ============================================================

from __future__ import annotations

from pathlib import Path
import pandas as pd


DIR_MASTER = Path("03_Master_Data")
DIR_UNMATCHED = DIR_MASTER / "unmatched addresses"
UNMATCHED_XLSX = DIR_UNMATCHED / "Unmatched_Addresses.xlsx"

MASTER_XLSX = DIR_MASTER / "Master Data.xlsx"
OUT_MASTER_XLSX = DIR_MASTER / "Master Data (SYSTEM CLEAN).xlsx"

REQUIRED_UNMATCHED_COLS = [
    "Parser",
    "Customer",
    "PDF Name",
    "Delivery Address (Extracted)",
    "Delivery Address Key (Master)",
    "Matched?",
    "Match Method",
    "Unmatched Match Key",
    "Notes",
]


def ensure_unmatched_schema():
    DIR_UNMATCHED.mkdir(parents=True, exist_ok=True)

    if not UNMATCHED_XLSX.exists():
        pd.DataFrame(columns=REQUIRED_UNMATCHED_COLS).to_excel(UNMATCHED_XLSX, index=False)
        return

    try:
        df = pd.read_excel(UNMATCHED_XLSX).fillna("")
    except Exception:
        pd.DataFrame(columns=REQUIRED_UNMATCHED_COLS).to_excel(UNMATCHED_XLSX, index=False)
        return

    changed = False
    for col in REQUIRED_UNMATCHED_COLS:
        if col not in df.columns:
            df[col] = ""
            changed = True

    if changed:
        df.to_excel(UNMATCHED_XLSX, index=False)


def clear_unmatched_file_preserve_columns():
    """
    Clears rows but preserves whatever columns exist (including diagnostics).
    """
    df = pd.read_excel(UNMATCHED_XLSX).fillna("")
    df.iloc[0:0].to_excel(UNMATCHED_XLSX, index=False)


def main():
    ensure_unmatched_schema()

    if not MASTER_XLSX.exists():
        raise FileNotFoundError(f"Master not found: {MASTER_XLSX}")

    df_master = pd.read_excel(MASTER_XLSX).fillna("")
    df_unmatched = pd.read_excel(UNMATCHED_XLSX).fillna("")

    if df_unmatched.empty:
        # Still write system clean copy so you can validate “runs cleanly”
        df_master.to_excel(OUT_MASTER_XLSX, index=False)
        return

    # Expect consultant to fill the key column
    key_col = "Delivery Address Key (Master)"
    if key_col not in df_unmatched.columns:
        df_master.to_excel(OUT_MASTER_XLSX, index=False)
        return

    # Add new rows to master where key is provided and not already present
    master_key_col = "Delivery Address Key"
    if master_key_col not in df_master.columns:
        # Create if missing
        df_master[master_key_col] = ""

    existing_keys = set(df_master[master_key_col].fillna("").astype(str).str.strip().tolist())

    additions = 0
    for _, unr in df_unmatched.iterrows():
        new_key = str(unr.get(key_col, "")).strip()
        if not new_key:
            continue

        if new_key in existing_keys:
            continue

        # Create new row with same columns as master
        new_row = {col: "" for col in df_master.columns}

        # If master has a “Delivery Address” (raw), populate it too (nice to have)
        if "Delivery Address" in df_master.columns:
            new_row["Delivery Address"] = str(unr.get("Delivery Address (Extracted)", "")).strip()

        # Set the KEY
        new_row[master_key_col] = new_key

        df_master = pd.concat([df_master, pd.DataFrame([new_row])], ignore_index=True)
        existing_keys.add(new_key)
        additions += 1

    # Write clean master output
    df_master.to_excel(OUT_MASTER_XLSX, index=False)

    # Clear unmatched rows after successful merge
    clear_unmatched_file_preserve_columns()


if __name__ == "__main__":
    main()
