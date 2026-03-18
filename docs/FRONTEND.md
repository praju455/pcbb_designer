# Nexus Frontend Guide

## Development

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the FastAPI backend at `http://localhost:8000`.

## Main pages

- Dashboard: overall system status and recent designs
- Generate: launch a pipeline run and watch live logs
- Validate: run DFM checks and review Gemini guidance
- Export: download fabrication bundles
- Settings: manage Groq, Gemini, and local Ollama values

## Deployment

- Frontend: Vercel
- Backend: Render or local FastAPI

## Backend connection indicator

The header includes a live backend connection badge driven by `/api/health`.
