"""AURA — Pulse 109 · FastAPI entry point.

Запуск: uvicorn main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import analytics, exports, similar, tickets

app = FastAPI(
    title="AURA — Pulse 109 API",
    description="Интеллектуальная платформа обработки обращений граждан (GovTech Camp 2026).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets.router)
app.include_router(similar.router)
app.include_router(analytics.router)
app.include_router(exports.router)


@app.get("/")
def root():
    return {"service": "AURA — Pulse 109", "status": "ok", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "healthy"}
