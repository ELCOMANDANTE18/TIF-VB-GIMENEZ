from fastapi import FastAPI

from app.webhook.router import router as webhook_router

app = FastAPI(title="Link Seguro")

app.include_router(webhook_router)


@app.get("/health")
def health():
    return {"status": "running"}
