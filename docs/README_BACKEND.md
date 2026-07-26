# Part 2 Backend Scaffold

## What this includes

- FastAPI app in `backend/main.py`
- Static hello-world page served at `/`
- Health endpoint: `GET /health`
- Sample endpoint: `GET /api/sample`
- Dockerfile at repo root
- Start/stop scripts in `scripts/` for Linux/macOS/Windows

## Run with Docker

```bash
docker build -t pm-backend .
docker run --rm -p 8000:8000 pm-backend
```

## Endpoints

- `/`
- `/health`
- `/api/sample`
