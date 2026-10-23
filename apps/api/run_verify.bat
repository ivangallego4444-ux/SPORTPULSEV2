@echo off
cd /d "%~dp0"
"C:\Users\iviro\OneDrive\Escritorio\SportPulse-v2\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8020
