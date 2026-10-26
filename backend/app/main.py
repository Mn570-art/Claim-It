"""Claim-It API."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.analysis import router as analysis_router
from app.api.claims import demo_router, router as claims_router
from app.api.documents import router as documents_router
from app.api.exports import router as exports_router
from app.api.settings import purge_expired, router as settings_router
from app.api.voice import router as voice_router
from app.core.config import get_settings
from app.core.database import get_db, init_db
from app.core.errors import AppError
from app.services.demo import sample_paths
from app.services.sarvam_client import build_client
from app.services.workflow import DISCLAIMER

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("claimit")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Claim-It", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.sarvam_client_factory = build_client
    init_db(settings)
    sample_paths()
    db_gen = get_db()
    db = next(db_gen)
    try:
        removed = purge_expired(db)
        if removed:
            logger.info("retention removed %s claim(s)", removed)
    finally:
        db_gen.close()

    app.include_router(claims_router)
    app.include_router(demo_router)
    app.include_router(documents_router)
    app.include_router(voice_router)
    app.include_router(analysis_router)
    app.include_router(exports_router)
    app.include_router(settings_router)

    @app.exception_handler(AppError)
    async def app_error(_request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        safe_errors = []
        for error in exc.errors():
            safe_errors.append(
                {
                    "loc": [str(part) for part in error.get("loc", [])],
                    "msg": str(error.get("msg", "Invalid value")),
                    "type": str(error.get("type", "value_error")),
                }
            )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "The request is not valid.",
                    "details": {"errors": safe_errors},
                }
            },
        )

    @app.get("/health")
    def health():
        current = get_settings()
        return {
            "status": "ok",
            "sarvam_configured": current.sarvam_configured,
            "demo_available": True,
            "disclaimer": DISCLAIMER,
        }

    return app


app = create_app()
