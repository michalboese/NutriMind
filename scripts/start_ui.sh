#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "[ERROR] Ollama is not running. Start it first: ollama run llama3.2"
    exit 1
fi

source venv/Scripts/activate 2>/dev/null || source venv/bin/activate
echo "Starting Gradio UI on http://localhost:7860"
python ui/gradio_app.py
