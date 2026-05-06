@echo off
cd /d "%~dp0.."

echo Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Ollama is not running. Start it first: ollama run qwen2.5:14b
    pause
    exit /b 1
)

echo Starting FastAPI backend in new window...
start "Calorie Agent - API" cmd /k "cd /d %~dp0.. && call venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

echo Waiting for API to start...
timeout /t 3 /nobreak >nul

echo Starting Gradio UI in new window...
start "Calorie Agent - UI" cmd /k "cd /d %~dp0.. && call venv\Scripts\activate.bat && python ui\gradio_app.py"

echo.
echo Both services starting:
echo   API:  http://localhost:8000/docs
echo   UI:   http://localhost:7860
