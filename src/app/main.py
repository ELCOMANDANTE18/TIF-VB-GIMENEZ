from fastapi import FastAPI

from app.dashboard.router import router as dashboard_router
from app.webhook.router import router as webhook_router

app = FastAPI(title="Link Seguro")

app.include_router(webhook_router)
app.include_router(dashboard_router)


@app.get("/health")
def health():
    return {"status": "running"}
