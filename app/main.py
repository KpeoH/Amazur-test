from fastapi import FastAPI

from app.api.v1.campaigns import router as campaign_router

app = FastAPI(title="Campaign Manager", version="1.0.0")

app.include_router(campaign_router, prefix="/api/v1")
