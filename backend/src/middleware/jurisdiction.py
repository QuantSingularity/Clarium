"""
Jurisdiction Enforcement Middleware
Reads X-Jurisdiction header and attaches active rules to request state.
Services can then enforce rules without repeating lookup logic.
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..services.rule_engine import get_rule_engine

logger = logging.getLogger("clarium.jurisdiction")


class JurisdictionMiddleware(BaseHTTPMiddleware):
    """
    Reads the X-Jurisdiction request header.
    Attaches the resolved rule set to request.state.jurisdiction_rules.
    Downstream handlers can access: request.state.jurisdiction (str)
    and request.state.jurisdiction_rules (dict | None).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        jurisdiction = request.headers.get(
            "X-Jurisdiction"
        ) or request.query_params.get("jurisdiction")

        request.state.jurisdiction = jurisdiction
        request.state.jurisdiction_rules = None

        if jurisdiction:
            engine = get_rule_engine()
            rules = engine.get(jurisdiction)
            if rules:
                request.state.jurisdiction_rules = rules
                logger.debug(f"Jurisdiction resolved: {jurisdiction}")
            else:
                logger.debug(f"Unknown jurisdiction: {jurisdiction} - no rules applied")

        return await call_next(request)
