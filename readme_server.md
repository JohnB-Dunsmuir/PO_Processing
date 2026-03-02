PO Processing – Server Deployment Guide
Overview

This application processes Purchase Order (PO) PDFs and generates structured Excel/CSV outputs.

The application runs entirely within the corporate network and does not rely on any external APIs or cloud services.

All document processing is local.

1. System Requirements

Windows VM (Windows 10/11 or Windows Server)

4 GB RAM minimum (8 GB recommended)

Internal network access for users

Port 8501 open internally

No database required.
No admin-level services required beyond Python installation.

2. Install Python

Download Python (3.10+) from python.org.

During installation:

✔ Add Python to PATH

✔ Install for current user (admin not required unless policy dictates)

Verify installation:

python --version
3. Deploy Application Files

Copy the entire project folder to the VM.

The folder must include:

streamlit_app.py
run_v12_wrapper_stdout.py
diagnose_one_pdf.py
diagnose_one_pdf_wrapper.py
build_extractor_output.py
Parsers/
01_PDFs/
02_Parsed_Data/
03_Master_Data/
04_Archive/
requirements.txt

Do not restructure folders.

4. Create Virtual Environment

From the project root:

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

Verify Streamlit:

python -m streamlit --version
5. Run the Application

From project root:

python -m streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501

Expected output:

Local URL: http://localhost:8501
Network URL: http://<vm-ip>:8501

Users access via:

http://<vm-ip>:8501
6. File Handling Model

Uploaded PDFs are stored locally in 01_PDFs/

Processed outputs are written to 02_Parsed_Data/

Archived PDFs are stored in 04_Archive/

Users download outputs directly via browser

No shared drives required.

7. Optional – Auto Start on Boot

If required:

Use Windows Task Scheduler

Trigger at system startup

Run the same Streamlit command

Ensure .venv is activated in task action

8. Security Notes

No external APIs

No cloud OCR

No outbound data transmission

All processing is local

No database connectivity

9. Troubleshooting

If the app does not start:

Confirm Python is installed.

Confirm virtual environment is activated.

Confirm pip install -r requirements.txt completed successfully.

Confirm port 8501 is not blocked internally.

Operational Status

This application is portable and server-ready.

No code changes are required for VM deployment.