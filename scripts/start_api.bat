@echo off
cd /d "%~dp0.."

echo Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Ollama is not running. Start it first: ollama run qwen2.5:14b
    pause
    exit /b 1
)

echo Starting FastAPI backend...
call venv\Scripts\activate.bat
uvicorn app.main:app --reload --port 8000
