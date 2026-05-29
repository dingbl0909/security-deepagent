from fastapi import FastAPI

from security_agent.api import alarms, chat, devices, health, reviews, threads
from security_agent.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Private security operations Agent platform.",
    )
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(threads.router)
    app.include_router(reviews.router)
    app.include_router(devices.router)
    app.include_router(alarms.router)
    return app


app = create_app()

