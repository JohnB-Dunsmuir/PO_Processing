import os, glob, subprocess, sys

FOLDER = r"C:\Users\EB005205\OneDrive - TE Connectivity\PO_Processing\Medical PDF"

print("\n=== SCANNING MEDICAL PDF FOLDER ===\n")

if not os.path.exists(FOLDER):
    print("Folder not found:", FOLDER)
    sys.exit(1)

pdfs = sorted(glob.glob(os.path.join(FOLDER, "*.pdf")))
if not pdfs:
    print("No PDFs found.")
    sys.exit(0)

for p in pdfs:
    try:
        out = subprocess.check_output([sys.executable, "diagnose_one_pdf.py", p], text=True, errors="ignore")
    except subprocess.CalledProcessError as e:
        out = e.output or ""

    status = "UNKNOWN"
    parser = "NONE"
    for line in out.splitlines():
        if "Detected parser module:" in line:
            parser = line.strip()
        if "[PASS]" in line:
            status = "PASS"
        if "[FAIL]" in line:
            status = "FAIL"

    print(f"{status:5} | {os.path.basename(p)} | {parser}")
