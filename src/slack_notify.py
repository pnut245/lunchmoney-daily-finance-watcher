"""Optional Slack webhook delivery for watcher completion summaries."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests


def send_weekly_summary(
    weekly_path: Path,
    alarm_path: Path,
    rule_hit_count: int,
    review_item_count: int,
    budget_config: dict[str, Any],
) -> bool:
    slack_config = budget_config.get("slack", {})
    webhook_env = str(slack_config.get("webhook_env", "SLACK_WEBHOOK_URL"))
    webhook_url = os.environ.get(webhook_env)
    if not webhook_url:
        raise RuntimeError(f"Missing required environment variable: {webhook_env}")

    message = build_weekly_summary_message(
        weekly_path,
        alarm_path,
        rule_hit_count,
        review_item_count,
        budget_config,
    )
    response = requests.post(webhook_url, json={"text": message}, timeout=20)
    if response.status_code >= 400:
        raise RuntimeError(
            f"Slack webhook failed with {response.status_code}: {response.text[:300]}"
        )
    return True


def build_weekly_summary_message(
    weekly_path: Path,
    alarm_path: Path,
    rule_hit_count: int,
    review_item_count: int,
    budget_config: dict[str, Any],
) -> str:
    slack_config = budget_config.get("slack", {})
    title = str(slack_config.get("title", "Sunday budget brief is ready"))
    include_paths = bool(slack_config.get("include_local_paths", True))

    lines = [
        f"*{title}*",
        f"- Review items: {review_item_count}",
        f"- Rule hits checked: {rule_hit_count}",
    ]
    if include_paths:
        lines.extend(
            [
                f"- Weekly brief: `{weekly_path}`",
                f"- Detail report: `{alarm_path}`",
            ]
        )
    return "\n".join(lines)
