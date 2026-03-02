@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo Virtual environment not found.
    echo Please contact J.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

python -m streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=8501

pause