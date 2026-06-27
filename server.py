import os
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pathlib import Path
import shutil
from fastapi.middleware.cors import CORSMiddleware
from core.exceptions.handler import APIException
from core.messages import *
from contextlib import asynccontextmanager
# from prometheus_client import make_asgi_app
from prometheus_fastapi_instrumentator import Instrumentator
from lib.payment.payment_router import router as payment_router 

from core.schemas.payment_schemas import API_Resolution

app = FastAPI(
    title="Finance API",
    description="Standalone finance microservice",
    version="0.1.0",
    openapi_url="/finance/openapi.json",  # Move OpenAPI to `/api/openapi.json`
    docs_url="/finance/docs",  # Keep Swagger UI at `/docs`
    redoc_url="/finance/redoc"  # Keep ReDoc at `/redoc`
)

# app.mount("/metrics", make_asgi_app())
Instrumentator().instrument(app).expose(app)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # If it's a known APIException
    if isinstance(exc, APIException):
        resolution = API_Resolution(
            status=exc.status,
            error_code=exc.code,
            message=str(exc.details),
        )
        return JSONResponse(
            status_code=exc.status,
            content=resolution.dict(),
        )
    status_code = HTTP_500_INTERNAL_SERVER_ERROR
    # If it's an unexpected internal error
    resolution = API_Resolution(
        status=status_code,
        error_code=INTERNAL_SERVER_ERROR,
        message=str(exc),
    )
    return JSONResponse(
        status_code=status_code,
        content=resolution.dict(),
    )



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for security in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payment_router, prefix="/payments", tags=["Payment routes"])
