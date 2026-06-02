"""Read-only Lunch Money v2 API client.

All Lunch Money endpoint assumptions live in this module so v2 alpha changes do
not leak into storage, rule, or reporting code.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

import requests


DEFAULT_BASE_URL = "https://api.lunchmoney.dev/v2"
DEFAULT_V1_BASE_URL = "https://dev.lunchmoney.app/v1"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_PAGE_LIMIT = 1000


class LunchMoneyAPIError(RuntimeError):
    """Raised when Lunch Money returns a failed response."""


@dataclass(frozen=True)
class OptionalResult:
    name: str
    payload: dict[str, Any]
    warning: str | None = None


class LunchMoneyClient:
    """Small read-only wrapper around Lunch Money API v2."""

    def __init__(
        self,
        access_token: str | None = None,
        base_url: str | None = None,
        v1_base_url: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        token = access_token or os.environ.get("LUNCHMONEY_ACCESS_TOKEN")
        if not token:
            raise ValueError(
                "Missing LUNCHMONEY_ACCESS_TOKEN. Export it before calling the API."
            )

        self.base_url = (base_url or os.environ.get("LUNCHMONEY_API_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.v1_base_url = (
            v1_base_url or os.environ.get("LUNCHMONEY_V1_API_BASE_URL") or DEFAULT_V1_BASE_URL
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "lunchmoney-daily-finance-watcher/0.1",
            }
        )

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        return self._get_url(url, path, params)

    def _get_v1(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.v1_base_url}/{path.lstrip('/')}"
        return self._get_url(url, f"v1/{path.lstrip('/')}", params)

    def _get_url(self, url: str, label: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.get(url, params=_clean_params(params), timeout=self.timeout_seconds)
        if response.status_code >= 400:
            body = response.text[:500]
            raise LunchMoneyAPIError(f"GET {label} failed with {response.status_code}: {body}")
        if not response.content:
            return {}
        payload = response.json()
        if isinstance(payload, list):
            return {"items": payload}
        if not isinstance(payload, dict):
            return {"value": payload}
        return payload

    def get_transactions(
        self,
        start_date: date,
        end_date: date,
        *,
        include_pending: bool = True,
    ) -> dict[str, Any]:
        transactions: list[dict[str, Any]] = []
        offset = 0
        use_pending_param = include_pending

        while True:
            params = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "limit": DEFAULT_PAGE_LIMIT,
                "offset": offset,
            }
            if use_pending_param:
                params["include_pending"] = True
            try:
                payload = self._get("/transactions", params)
            except LunchMoneyAPIError as exc:
                # v2 alpha currently validates query booleans strictly in some
                # environments. Pending inclusion is useful but not required.
                if use_pending_param and "include_pending" in str(exc):
                    use_pending_param = False
                    continue
                raise
            page = _extract_list(payload, "transactions")
            transactions.extend(page)
            if not payload.get("has_more") or not page:
                break
            offset += len(page)
            time.sleep(0.15)

        return {"transactions": transactions, "has_more": False}

    def get_categories(self) -> dict[str, Any]:
        payload = self._get("/categories", {"format": "flattened"})
        categories = _extract_list(payload, "categories")
        if categories:
            return payload

        fallback = self.get_categories_v1()
        fallback_categories = _extract_list(fallback, "categories")
        if fallback_categories:
            fallback["_source"] = "v1_fallback"
            return fallback
        return payload

    def get_categories_v1(self) -> dict[str, Any]:
        return self._get_v1("/categories")

    def get_tags_v1(self) -> dict[str, Any]:
        payload = self._get_v1("/tags")
        if "items" in payload and "tags" not in payload:
            return {"tags": payload["items"], "_source": "v1"}
        return payload

    def get_manual_accounts(self) -> dict[str, Any]:
        return self._get("/manual_accounts")

    def get_plaid_accounts(self) -> dict[str, Any]:
        return self._get("/plaid_accounts")

    def get_recurring_items(self, start_date: date, end_date: date) -> dict[str, Any]:
        return self._get(
            "/recurring_items",
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

    def get_budget_settings(self) -> dict[str, Any]:
        return self._get("/budgets/settings")

    def get_budget_summary(self, start_date: date, end_date: date) -> dict[str, Any]:
        return self._get(
            "/summary",
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )


def pull_read_only_snapshot(
    client: LunchMoneyClient,
    start_date: date,
    end_date: date,
    budget_start_date: date,
    budget_end_date: date,
    *,
    include_pending: bool = True,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Fetch the read-only resources used by the watcher."""

    payloads: dict[str, dict[str, Any]] = {
        "transactions": client.get_transactions(
            start_date, end_date, include_pending=include_pending
        ),
        "categories": client.get_categories(),
    }
    warnings: list[str] = []

    optional_calls = [
        ("manual_accounts", client.get_manual_accounts),
        ("plaid_accounts", client.get_plaid_accounts),
        ("recurring_items", lambda: client.get_recurring_items(budget_start_date, budget_end_date)),
        ("budget_settings", client.get_budget_settings),
        ("budget_summary", lambda: client.get_budget_summary(budget_start_date, budget_end_date)),
        ("tags", client.get_tags_v1),
    ]

    for name, call in optional_calls:
        result = _optional(name, call)
        payloads[name] = result.payload
        if result.warning:
            warnings.append(result.warning)

    return payloads, warnings


def _optional(name: str, call: Any) -> OptionalResult:
    try:
        return OptionalResult(name=name, payload=call())
    except Exception as exc:  # Keep optional alpha endpoints from blocking core pulls.
        return OptionalResult(name=name, payload={}, warning=f"{name}: {exc}")


def _extract_list(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key)
    if isinstance(value, dict):
        nested = value.get(key)
        if isinstance(nested, list):
            value = nested
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    items = payload.get("items")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def _clean_params(params: dict[str, Any] | None) -> dict[str, Any]:
    if not params:
        return {}
    return {key: value for key, value in params.items() if value is not None}
