"""AURA — Pulse 109 · FastAPI entry point.

Запуск: uvicorn main:app --reload --port 8000
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from routes import analytics, exports, similar, tickets

app = FastAPI(
    title="AURA — Pulse 109 API",
    description="Интеллектуальная платформа обработки обращений граждан (GovTech Camp 2026).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    # В проде фронтенд и API на одном origin, но localhost оставляем для разработки.
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://arbybyby.govtech-kz.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets.router)
app.include_router(similar.router)
app.include_router(analytics.router)
app.include_router(exports.router)


# ---------------------------------------------------------------------------
# Статика фронтенда
# ---------------------------------------------------------------------------
# В проде собранный Vite-билд раздаётся тем же процессом на том же порту:
# организаторы дают один порт (8008), поднимать отдельный nginx незачем.
# Локально папки dist нет — тогда корень отдаёт JSON, как раньше.
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


# Объявлять ДО catch-all ниже: FastAPI подбирает роуты в порядке регистрации,
# и "/{full_path:path}" перехватил бы этот путь.
@app.get("/api/health")
def health():
    return {"status": "healthy"}


if FRONTEND_DIST.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        """Любой не-API путь отдаёт index.html — роутинг на стороне React.

        Путь из URL обязательно проверяется на выход за пределы dist: без
        этого «../../etc/passwd» отдал бы произвольный файл с сервера.
        Starlette сейчас нормализует путь до роутинга, но закладываться на
        это нельзя — проверяем сами.
        """
        base = FRONTEND_DIST.resolve()
        index = base / "index.html"
        if not full_path:
            return FileResponse(index)

        candidate = (base / full_path).resolve()
        try:
            candidate.relative_to(base)
        except ValueError:
            # запрошенное лежит вне dist — наружу ничего не отдаём
            return FileResponse(index)

        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)

else:

    @app.get("/")
    def root():
        return {"service": "AURA — Pulse 109", "status": "ok", "docs": "/docs"}
