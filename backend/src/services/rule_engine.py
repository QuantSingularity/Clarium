"""
Clarium Jurisdiction Rule Engine
=================================
Loads per-country compliance rules from YAML files and exposes them for enforcement.
Rules cover: transaction limits, disclosure requirements, age gates, KYC tiers.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import yaml

from ..config import settings

logger = logging.getLogger("clarium.rules")


class JurisdictionRuleEngine:
    """
    Loads and caches jurisdiction rules from YAML files.
    File naming: {rules_dir}/{jurisdiction}.yaml  e.g. US.yaml, GB.yaml
    """

    def __init__(self, rules_dir: str):
        self.rules_dir = rules_dir
        self._cache: Dict[str, Dict] = {}
        self._load_all()

    def _load_all(self):
        if not os.path.isdir(self.rules_dir):
            logger.warning(f"Rules directory not found: {self.rules_dir}")
            return
        for fname in os.listdir(self.rules_dir):
            if fname.endswith((".yaml", ".yml")):
                code = fname.split(".")[0].upper()
                self._load(code, os.path.join(self.rules_dir, fname))

    def _load(self, code: str, path: str):
        try:
            with open(path) as f:
                rules = yaml.safe_load(f)
            self._cache[code] = rules
            logger.info(f"Loaded rules for jurisdiction: {code}")
        except Exception as e:
            logger.error(f"Failed to load rules for {code}: {e}")

    def get(self, jurisdiction: str) -> Optional[Dict[str, Any]]:
        return self._cache.get(jurisdiction.upper())

    def list_jurisdictions(self) -> List[str]:
        return sorted(self._cache.keys())

    def check_transaction_limit(
        self, jurisdiction: str, amount: float, currency: str
    ) -> Dict[str, Any]:
        """Check if a transaction amount exceeds jurisdiction-specific limits."""
        rules = self.get(jurisdiction)
        if not rules:
            return {"allowed": True, "reason": "No rules defined for jurisdiction"}

        limits = rules.get("transaction_limits", {})
        max_single = limits.get("max_single_transaction")
        if max_single and amount > max_single:
            return {
                "allowed": False,
                "reason": (
                    f"Transaction of {amount} {currency} exceeds "
                    f"{jurisdiction} limit of {max_single}"
                ),
                "limit": max_single,
            }
        return {"allowed": True}

    def check_age_gate(self, jurisdiction: str, age_years: float) -> Dict[str, Any]:
        """Check if a user meets the minimum age requirement."""
        rules = self.get(jurisdiction)
        if not rules:
            return {"allowed": True}

        min_age = rules.get("age_gate", {}).get("minimum_age", 18)
        if age_years < min_age:
            return {
                "allowed": False,
                "reason": f"Minimum age {min_age} required in {jurisdiction}",
                "min_age": min_age,
            }
        return {"allowed": True}

    def get_disclosures(self, jurisdiction: str) -> List[str]:
        """Get required disclosures for a jurisdiction."""
        rules = self.get(jurisdiction)
        if not rules:
            return []
        return rules.get("required_disclosures", [])

    def get_kyc_tier(self, jurisdiction: str, amount: float) -> str:
        """Determine the KYC tier required for a given transaction amount."""
        rules = self.get(jurisdiction)
        if not rules:
            return "standard"
        tiers = rules.get("kyc_tiers", [])
        for tier in sorted(tiers, key=lambda t: t.get("threshold", 0), reverse=True):
            if amount >= tier.get("threshold", 0):
                return tier.get("level", "standard")
        return "basic"

    def reload(self):
        """Reload all rules from disk (hot-reload without restart)."""
        self._cache.clear()
        self._load_all()
        logger.info("Rules reloaded from disk")


# Singleton
_engine: Optional[JurisdictionRuleEngine] = None


def get_rule_engine() -> JurisdictionRuleEngine:
    global _engine
    if _engine is None:
        _engine = JurisdictionRuleEngine(settings.rules_dir)
    return _engine
