"""
Clarium AML Rule Engine
=======================
Flags transactions using four independent checks:
  1. Amount threshold - single transaction above limit
  2. Velocity         - too many transactions in a time window
  3. Geographic risk  - high-risk source/destination countries
  4. PEP matching     - sender/receiver on Politically Exposed Persons list
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import AMLCheck, PEPEntry

logger = logging.getLogger("clarium.aml")

# ── Geographic Risk Scores (ISO 3166-1 alpha-2) ───────────────────────────────
# Score 0.0 = low risk, 1.0 = very high risk
COUNTRY_RISK_SCORES: Dict[str, float] = {
    # High risk jurisdictions
    "AF": 0.95,
    "KP": 0.98,
    "IR": 0.92,
    "SY": 0.93,
    "YE": 0.88,
    "LY": 0.85,
    "SO": 0.87,
    "SD": 0.82,
    "MM": 0.80,
    "VE": 0.78,
    "CU": 0.75,
    "BY": 0.72,
    "RU": 0.70,
    "CN": 0.45,
    "NG": 0.62,
    # Medium risk
    "MX": 0.55,
    "PK": 0.60,
    "UA": 0.50,
    "TR": 0.42,
    "EG": 0.48,
    # Low risk (FATF members)
    "US": 0.05,
    "GB": 0.05,
    "DE": 0.05,
    "FR": 0.06,
    "JP": 0.04,
    "CA": 0.05,
    "AU": 0.05,
    "CH": 0.06,
    "SG": 0.06,
    "NL": 0.05,
}
DEFAULT_COUNTRY_RISK = 0.35


def _country_risk(country: Optional[str]) -> float:
    if not country:
        return DEFAULT_COUNTRY_RISK
    return COUNTRY_RISK_SCORES.get(country.upper(), DEFAULT_COUNTRY_RISK)


async def run_aml_check(
    db: AsyncSession,
    transaction_id: str,
    user_id: Optional[str],
    amount: float,
    currency: str,
    source_country: Optional[str],
    destination_country: Optional[str],
) -> Tuple[float, bool, List[str], bool, Optional[Dict]]:
    """
    Run all AML rules. Returns:
        (risk_score, flagged, flag_reasons, pep_match, pep_details)
    """
    flag_reasons: List[str] = []
    risk_score = 0.0

    # ── Rule 1: Amount threshold ──────────────────────────────────────────────
    if amount >= settings.aml_amount_threshold:
        flag_reasons.append(
            f"Amount {amount:.2f} {currency} exceeds threshold "
            f"{settings.aml_amount_threshold:.2f}"
        )
        risk_score += 0.40
        logger.info(f"AML [amount] txn={transaction_id} amount={amount}")

    # ── Rule 2: Velocity check ────────────────────────────────────────────────
    if user_id:
        window_start = datetime.now(timezone.utc) - timedelta(
            minutes=settings.aml_velocity_window_minutes
        )
        velocity_result = await db.execute(
            select(func.count(AMLCheck.id)).where(
                and_(
                    AMLCheck.user_id == user_id,
                    AMLCheck.checked_at >= window_start,
                )
            )
        )
        recent_count = velocity_result.scalar_one() or 0

        if recent_count >= settings.aml_velocity_max_transactions:
            flag_reasons.append(
                f"Velocity: {recent_count} transactions in "
                f"{settings.aml_velocity_window_minutes} minutes "
                f"(limit: {settings.aml_velocity_max_transactions})"
            )
            risk_score += 0.35
            logger.info(f"AML [velocity] txn={transaction_id} count={recent_count}")

    # ── Rule 3: Geographic risk ───────────────────────────────────────────────
    src_risk = _country_risk(source_country)
    dst_risk = _country_risk(destination_country)
    geo_risk = max(src_risk, dst_risk)

    if geo_risk >= 0.70:
        flag_reasons.append(
            f"Geographic risk: source={source_country}({src_risk:.2f}) "
            f"destination={destination_country}({dst_risk:.2f})"
        )
        risk_score += geo_risk * 0.20
        logger.info(f"AML [geo] txn={transaction_id} geo_risk={geo_risk}")
    else:
        risk_score += geo_risk * 0.05

    # ── Rule 4: PEP list matching ─────────────────────────────────────────────
    pep_match = False
    pep_details = None

    if user_id:
        pep_result = await db.execute(
            select(PEPEntry).where(PEPEntry.full_name.ilike(f"%{user_id}%")).limit(5)
        )
        pep_entries = pep_result.scalars().all()
        if pep_entries:
            pep_match = True
            pep_details = [
                {
                    "name": e.full_name,
                    "country": e.country,
                    "position": e.position,
                    "risk_level": e.risk_level,
                }
                for e in pep_entries
            ]
            flag_reasons.append(f"PEP match: {[e.full_name for e in pep_entries]}")
            risk_score += 0.50
            logger.info(f"AML [PEP] txn={transaction_id} matches={len(pep_entries)}")

    # Clamp risk score to [0, 1]
    risk_score = min(round(risk_score, 4), 1.0)
    flagged = risk_score >= settings.aml_high_risk_score or bool(flag_reasons)

    return risk_score, flagged, flag_reasons, pep_match, pep_details
