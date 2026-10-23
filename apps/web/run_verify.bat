@echo off
cd /d "%~dp0"
set NEXT_PUBLIC_API_URL=http://127.0.0.1:8020
npm run dev -- -p 3120
