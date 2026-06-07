from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.dashboard.router import router as dashboard_router
from app.webhook.router import router as webhook_router

app = FastAPI(title="Link Seguro")

_static_dir = Path(__file__).parent.parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

app.include_router(webhook_router)
app.include_router(dashboard_router)


@app.get("/health")
def health():
    return {"status": "running"}
