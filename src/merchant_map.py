"""Local merchant mapping suggestions.

This is intentionally local-only. It does not write categories back to Lunch Money.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


def load_merchant_map(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    rules = payload.get("merchant_map", [])
    return [rule for rule in rules if isinstance(rule, dict) and rule.get("match")]


def suggest_for_payee(payee: Any, rules: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized_payee = _normalize(payee)
    if not normalized_payee:
        return None
    for rule in rules:
        needle = _normalize(rule.get("match"))
        if needle and needle in normalized_payee:
            return {
                "match": rule.get("match"),
                "category": rule.get("category"),
                "confidence": rule.get("confidence", "medium"),
                "alert_policy": rule.get("alert_policy", "weekly_review"),
            }
    return None


def _normalize(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()
