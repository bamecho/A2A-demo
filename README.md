# Strands A2A Bridge (Phase 1)

Minimal FastAPI host with a mounted A2A server at `/a2a`.

## Run

```bash
uv sync
uv run uvicorn strands_a2a_bridge.app:create_app --factory --host 127.0.0.1 --port 8000
```

## Verify

```bash
uv run python -m pytest --version
uv run python -c "from strands_a2a_bridge.app import create_app; app = create_app(); print(app.title)"
uv run python -m pytest tests/integration/test_phase1_a2a_streaming.py -v
```
