#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "[ERROR] Ollama is not running. Start it first: ollama run qwen2.5:14b"
    exit 1
fi

source venv/Scripts/activate 2>/dev/null || source venv/bin/activate
echo "Starting FastAPI on http://localhost:8000"
uvicorn app.main:app --reload --port 8000
