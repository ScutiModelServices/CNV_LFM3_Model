@echo off
REM Starts the LFM3 service on port 9170 (syncs .venv with uv on each run). The first start downloads the weights (about 4 GB).
REM LABEL: LFM3 Service
REM DESCRIPTION: Shared HTTP service that runs LFM3-1.7B on the CPU for every project.

cd /d "%~dp0"

python -m uv sync
if errorlevel 1 (
    echo uv sync failed. Install uv: winget install astral-sh.uv
    pause
    exit /b 1
)
call .venv\Scripts\activate

python src/app.py
pause
