@echo off
setlocal
if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found.
  echo Create it with: python -m venv .venv
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m streamlit run app.py
