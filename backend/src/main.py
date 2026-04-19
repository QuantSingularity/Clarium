"""
Clarium - RegTech Compliance Module
FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import init_db
from .middleware.jurisdiction import JurisdictionMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .routers import admin, aml, audit, kyc, rules, webhooks

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("clarium")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Clarium API...")
    await init_db()
    yield
    logger.info("Clarium API shutdown.")


app = FastAPI(
    title="Clarium - RegTech Compliance Module",
    description=(
        "KYC pipeline, AML transaction monitoring, immutable audit trail, "
        "jurisdiction rule engine, and webhook notifications."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware (order matters: outermost first) ────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(JurisdictionMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(kyc.router, prefix="/kyc", tags=["KYC"])
app.include_router(aml.router, prefix="/aml", tags=["AML"])
app.include_router(audit.router, prefix="/audit", tags=["Audit Trail"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(rules.router, prefix="/rules", tags=["Jurisdiction Rules"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "service": "clarium", "version": "0.1.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
