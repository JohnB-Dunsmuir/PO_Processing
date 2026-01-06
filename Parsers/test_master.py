import pandas as pd

path = r"C:\Users\EB005205\OneDrive - TE Connectivity\PO_Processing\03_Master_Data\Master data updated 2025-12-05_19-56-17.xlsx"

df = pd.read_excel(path).fillna("")

row = df[df["Customer name"].astype(str).str.upper().str.strip() == "ANTALIS"]

print("\n*** ROWS FOUND:", len(row))
print(row.to_string())
