"""
Clarium Rate Limiting Middleware
Uses Redis sliding-window rate limiting per IP / API key.
"""

import logging
import time
from typing import Optional

import redis.asyncio as aioredis
from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..config import settings

logger = logging.getLogger("clarium.ratelimit")

# Rate limit config per route prefix
RATE_LIMITS = {
    "/kyc/submit": (10, 60),  # 10 requests / 60 seconds
    "/aml/check": (100, 60),  # 100 requests / 60 seconds
    "/kyc/upload": (5, 60),  # 5 uploads / 60 seconds
    "default": (200, 60),  # 200 requests / 60 seconds
}

_redis: Optional[aioredis.Redis] = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _get_limit(path: str):
    for prefix, limit in RATE_LIMITS.items():
        if prefix != "default" and path.startswith(prefix):
            return limit
    return RATE_LIMITS["default"]


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip health check and docs
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        max_req, window = _get_limit(path)

        key = f"clarium:rl:{client_ip}:{path}"
        now = int(time.time())
        window_key = f"{key}:{now // window}"

        try:
            r = await _get_redis()
            count = await r.incr(window_key)
            if count == 1:
                await r.expire(window_key, window * 2)

            if count > max_req:
                logger.warning(
                    f"Rate limit exceeded: ip={client_ip} path={path} count={count}"
                )
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": f"Too many requests. Limit: {max_req} per {window}s",
                        "retry_after": window - (now % window),
                    },
                )
        except HTTPException:
            raise
        except Exception as e:
            # Redis unavailable - fail open (don't block requests)
            logger.error(f"Rate limit Redis error: {e}")

        return await call_next(request)
