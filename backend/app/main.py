from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.response import fail
from app.mqtt.consumer import mqtt_consumer

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
def start_mqtt_consumer() -> None:
    mqtt_consumer.start()


@app.on_event("shutdown")
def stop_mqtt_consumer() -> None:
    mqtt_consumer.stop()


@app.exception_handler(Exception)
async def global_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content=fail(f"internal error: {exc}"))

