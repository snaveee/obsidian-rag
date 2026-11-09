@echo off
echo Starting obsidian-rag FastAPI Backend on port 8001...
uvicorn infra.main:app --host 127.0.0.1 --port 8001 --reload

