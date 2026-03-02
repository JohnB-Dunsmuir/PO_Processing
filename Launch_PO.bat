@echo off
cd /d "%~dp0"

echo Starting PO Processing (Streamlit)...
echo.

streamlit run streamlit_app.py

pause