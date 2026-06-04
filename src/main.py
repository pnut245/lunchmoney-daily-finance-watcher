"""CLI entrypoint for the Lunch Money local finance watcher."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from . import alarms, budget_state, finance_ask, one_number, report, rules, slack_notify, storage, weekly_email
from .lunchmoney_client import LunchMoneyClient, pull_read_only_snapshot


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "lunchmoney.db"
DEFAULT_RAW_ROOT = PROJECT_ROOT / "data" / "raw"
DEFAULT_REPORTS_ROOT = PROJECT_ROOT / "reports"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "rules.yaml"
DEFAULT_BUDGET_PATH = PROJECT_ROOT / "config" / "budget.yaml"
DEFAULT_MERCHANT_MAP_PATH = PROJECT_ROOT / "config" / "merchant_map.yaml"
README_SETUP_REFERENCE = f"See {PROJECT_ROOT / 'README.md'} Quick Start."
LUNCHMONEY_ACCESS_TOKEN_PLACEHOLDERS = {
    "replace_with_your_lunch_money_access_token",
    "your_lunch_money_access_token",
    "replace_me",
    "changeme",
}


class ConfigurationValidationError(ValueError):
    """Raised when required local configuration is missing."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Local-first Lunch Money finance watcher")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--budget", type=Path, default=DEFAULT_BUDGET_PATH)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--reports-root", type=Path, default=DEFAULT_REPORTS_ROOT)
    parser.add_argument("--merchant-map", type=Path, default=DEFAULT_MERCHANT_MAP_PATH)

    subparsers = parser.add_subparsers(dest="command", required=True)

    pull_parser = subparsers.add_parser("pull", help="Pull read-only data from Lunch Money")
    pull_parser.add_argument("--start-date", type=_parse_date)
    pull_parser.add_argument("--end-date", type=_parse_date)
    pull_parser.add_argument("--date", type=_parse_date, default=date.today())

    check_parser = subparsers.add_parser("check", help="Run local rule checks")
    check_parser.add_argument("--date", type=_parse_date, default=date.today())

    report_parser = subparsers.add_parser("report", help="Write markdown report")
    report_parser.add_argument("--date", type=_parse_date, default=date.today())

    run_parser = subparsers.add_parser("run-all", help="Pull, check, and report")
    run_parser.add_argument("--date", type=_parse_date, default=date.today())
    run_parser.add_argument("--start-date", type=_parse_date)
    run_parser.add_argument("--end-date", type=_parse_date)

    alarm_parser = subparsers.add_parser("alarms", help="Write alarm-only budget trigger report")
    alarm_parser.add_argument("--date", type=_parse_date, default=date.today())
    alarm_parser.add_argument("--notify", action="store_true", help="Send a local notification if alarms match notify policy")

    monitor_parser = subparsers.add_parser("monitor", help="Pull, check, and write alarm report only")
    monitor_parser.add_argument("--date", type=_parse_date, default=date.today())
    monitor_parser.add_argument("--start-date", type=_parse_date)
    monitor_parser.add_argument("--end-date", type=_parse_date)
    monitor_parser.add_argument("--notify", action="store_true", help="Send a local notification if alarms match notify policy")

    sample_parser = subparsers.add_parser("sample-report", help="Generate a mocked sample report")
    sample_parser.add_argument("--date", type=_parse_date, default=date.today())

    sample_alarms_parser = subparsers.add_parser("sample-alarms", help="Generate a mocked alarm report")
    sample_alarms_parser.add_argument("--date", type=_parse_date, default=date.today())

    weekly_parser = subparsers.add_parser("weekly-email", help="Pull, check, and write weekly budget email")
    weekly_parser.add_argument("--date", type=_parse_date, default=date.today())
    weekly_parser.add_argument("--start-date", type=_parse_date)
    weekly_parser.add_argument("--end-date", type=_parse_date)
    weekly_parser.add_argument("--no-pull", action="store_true", help="Use already stored data instead of pulling first")
    weekly_parser.add_argument("--send", action="store_true", help="Send via SMTP environment variables")
    weekly_parser.add_argument("--slack", action="store_true", help="Post completion summary to Slack webhook")

    sample_weekly_parser = subparsers.add_parser("sample-weekly-email", help="Generate a mocked weekly email")
    sample_weekly_parser.add_argument("--date", type=_parse_date, default=date.today())

    ask_parser = subparsers.add_parser("ask", help="Build a local finance question packet")
    ask_parser.add_argument("question", help="Financial question to answer from local watcher context")
    ask_parser.add_argument("--date", type=_parse_date, default=date.today())

    merchant_parser = subparsers.add_parser("merchant-summary", help="Summarize recent spend for one merchant")
    merchant_parser.add_argument("merchant", help="Merchant/payee search text")
    merchant_parser.add_argument("--date", type=_parse_date, default=date.today())
    merchant_parser.add_argument("--days", type=int, default=30)

    impact_parser = subparsers.add_parser("impact", help="Estimate how a purchase affects local budgets")
    impact_parser.add_argument("amount", type=float, help="Purchase amount")
    impact_parser.add_argument("--category", help="Budget category to test")
    impact_parser.add_argument("--merchant", help="Merchant/payee text for local category suggestion")
    impact_parser.add_argument("--date", type=_parse_date, default=date.today())

    one_number_parser = subparsers.add_parser("one-number-state", help="Write One Number Today JSON state")
    one_number_parser.add_argument("--date", type=_parse_date, default=date.today())

    close_month_parser = subparsers.add_parser("one-number-close-month", help="Store a One Number Today month-end ledger entry")
    close_month_parser.add_argument("--date", type=_parse_date, default=date.today())

    args = parser.parse_args()
    try:
        _validate_startup_configuration(args)
    except ConfigurationValidationError as exc:
        print(exc, file=sys.stderr)
        return 2

    config = rules.load_rules(args.config)
    budget_config = alarms.load_budget_config(args.budget)

    if args.command == "pull":
        pull(args.db_path, DEFAULT_RAW_ROOT, config, args.date, args.start_date, args.end_date)
    elif args.command == "check":
        run_id, hits = rules.run_checks(args.db_path, config, args.date)
        print(f"Rule run {run_id} created with {len(hits)} hit(s).")
    elif args.command == "report":
        run_id = storage.latest_rule_run_id(args.db_path, args.date)
        if run_id is None:
            run_id, _ = rules.run_checks(args.db_path, config, args.date)
        path = report.write_report(
            args.db_path,
            args.reports_root,
            args.date,
            run_id=run_id,
            max_flagged_transactions=int(config.get("report", {}).get("max_flagged_transactions", 40)),
        )
        print(f"Report written to {path}")
    elif args.command == "run-all":
        pull(args.db_path, DEFAULT_RAW_ROOT, config, args.date, args.start_date, args.end_date)
        run_id, hits = rules.run_checks(args.db_path, config, args.date)
        path = report.write_report(
            args.db_path,
            args.reports_root,
            args.date,
            run_id=run_id,
            max_flagged_transactions=int(config.get("report", {}).get("max_flagged_transactions", 40)),
        )
        _refresh_lockscreen_state(args.db_path, budget_config, args.date)
        print(f"Pulled data, created rule run {run_id} with {len(hits)} hit(s), and wrote {path}")
    elif args.command == "alarms":
        path, active_alarms = write_alarm_outputs(
            args.db_path,
            args.reports_root,
            config,
            budget_config,
            args.date,
            notify=args.notify,
        )
        _refresh_lockscreen_state(args.db_path, budget_config, args.date, active_alarms=active_alarms)
        print(f"Alarm report written to {path} with {len(active_alarms)} active alarm(s).")
    elif args.command == "monitor":
        pull(args.db_path, DEFAULT_RAW_ROOT, config, args.date, args.start_date, args.end_date)
        run_id, hits = rules.run_checks(args.db_path, config, args.date)
        path, active_alarms = alarms.write_alarm_report(
            args.db_path,
            args.reports_root,
            run_id,
            args.date,
            budget_config,
        )
        _refresh_lockscreen_state(args.db_path, budget_config, args.date, active_alarms=active_alarms)
        notified = alarms.send_local_notification(active_alarms, budget_config) if args.notify else False
        notify_text = " Notification sent." if notified else ""
        print(
            f"Pulled data, created rule run {run_id} with {len(hits)} hit(s), "
            f"and wrote {path} with {len(active_alarms)} active alarm(s).{notify_text}"
        )
    elif args.command == "sample-report":
        path = generate_sample_report(args.reports_root, config, args.date)
        print(f"Sample report written to {path}")
    elif args.command == "sample-alarms":
        path = generate_sample_alarms(args.reports_root, config, budget_config, args.date)
        print(f"Sample alarm report written to {path}")
    elif args.command == "weekly-email":
        if not args.no_pull:
            pull(args.db_path, DEFAULT_RAW_ROOT, config, args.date, args.start_date, args.end_date)
        run_id, hits = rules.run_checks(args.db_path, config, args.date)
        alarm_path, active_alarms = alarms.write_alarm_report(
            args.db_path,
            args.reports_root,
            run_id,
            args.date,
            budget_config,
        )
        _refresh_lockscreen_state(args.db_path, budget_config, args.date, active_alarms=active_alarms)
        email_path, markdown = weekly_email.write_weekly_email(
            args.db_path,
            args.reports_root,
            run_id,
            args.date,
            budget_config,
        )
        if args.send:
            weekly_email.send_weekly_email(markdown, budget_config)
        posted_slack = args.slack or budget_config.get("slack", {}).get("enabled", False)
        if posted_slack:
            slack_notify.send_weekly_summary(
                email_path,
                alarm_path,
                len(hits),
                len(active_alarms),
                budget_config,
            )
        sent_text = " Sent email." if args.send else ""
        slack_text = " Posted Slack summary." if posted_slack else ""
        print(
            f"Weekly email written to {email_path}; alarm report written to {alarm_path}; "
            f"{len(hits)} rule hit(s), {len(active_alarms)} review item(s).{sent_text}{slack_text}"
        )
    elif args.command == "sample-weekly-email":
        path = generate_sample_weekly_email(args.reports_root, config, budget_config, args.date)
        print(f"Sample weekly email written to {path}")
    elif args.command == "ask":
        path = finance_ask.write_question_packet(
            args.db_path,
            args.reports_root,
            args.question,
            args.date,
            config,
            budget_config,
            args.merchant_map,
        )
        print(f"Finance question packet written to {path}")
    elif args.command == "merchant-summary":
        path = finance_ask.write_merchant_summary(
            args.db_path,
            args.reports_root,
            args.merchant,
            args.date,
            days=args.days,
            merchant_map_path=args.merchant_map,
        )
        print(f"Merchant summary written to {path}")
    elif args.command == "impact":
        path = finance_ask.write_purchase_impact(
            args.db_path,
            args.reports_root,
            args.amount,
            args.category,
            args.merchant,
            args.date,
            budget_config,
            args.merchant_map,
        )
        print(f"Purchase impact written to {path}")
    elif args.command == "one-number-state":
        outputs = budget_state.refresh_budget_state(
            args.db_path,
            budget_config,
            args.date,
            project_root=PROJECT_ROOT,
        )
        for path in outputs["json_paths"]:
            print(f"One Number Today state written to {path}")
        for path in outputs["widget_paths"]:
            print(f"Widget snapshot written to {path}")
        for path in outputs["settings_paths"]:
            print(f"Settings JSON written to {path}")
        for path in outputs["ledger_paths"]:
            print(f"Ledger JSON written to {path}")
    elif args.command == "one-number-close-month":
        entry = one_number.close_month(args.db_path, budget_config, args.date)
        print(
            "One Number Today ledger entry stored: "
            f"{entry['month']} {entry['result']:+.2f}"
        )

    return 0


def _validate_startup_configuration(args: argparse.Namespace) -> None:
    if not _command_requires_lunchmoney_token(args):
        return

    missing: list[str] = []
    invalid: list[str] = []
    token = os.environ.get("LUNCHMONEY_ACCESS_TOKEN", "").strip()
    if not token:
        missing.append("LUNCHMONEY_ACCESS_TOKEN")
    elif token.lower() in LUNCHMONEY_ACCESS_TOKEN_PLACEHOLDERS:
        invalid.append("LUNCHMONEY_ACCESS_TOKEN")

    if not missing and not invalid:
        return

    lines = ["Lunch Money setup is incomplete."]
    if missing:
        lines.append(f"Missing required environment variable(s): {', '.join(missing)}.")
    if invalid:
        lines.append(f"Invalid placeholder value for: {', '.join(invalid)}.")
    lines.extend(
        [
            "Export a real Lunch Money access token before running commands that pull live data.",
            "Example: export LUNCHMONEY_ACCESS_TOKEN=your_real_token",
            README_SETUP_REFERENCE,
        ]
    )
    raise ConfigurationValidationError("\n".join(lines))


def _command_requires_lunchmoney_token(args: argparse.Namespace) -> bool:
    if args.command in {"pull", "run-all", "monitor"}:
        return True
    return args.command == "weekly-email" and not bool(getattr(args, "no_pull", False))


def pull(
    db_path: Path,
    raw_root: Path,
    config: dict,
    run_date: date,
    start_date: date | None,
    end_date: date | None,
) -> None:
    lookback_days = int(config.get("pull", {}).get("lookback_days", 120))
    include_pending = bool(config.get("pull", {}).get("include_pending", True))
    end = end_date or run_date
    start = start_date or (end - timedelta(days=lookback_days))
    budget_start = run_date.replace(day=1)
    budget_end = _month_end(run_date)

    client = LunchMoneyClient()
    payloads, warnings = pull_read_only_snapshot(
        client,
        start,
        end,
        budget_start,
        budget_end,
        include_pending=include_pending,
    )
    storage.save_pull_snapshot(db_path, raw_root, run_date, payloads, warnings)
    print(f"Pulled Lunch Money data for {start.isoformat()} through {end.isoformat()}.")
    if warnings:
        print("Optional endpoint warnings:")
        for warning in warnings:
            print(f"- {warning}")


def _refresh_lockscreen_state(
    db_path: Path,
    budget_config: dict[str, object],
    run_date: date,
    *,
    active_alarms: list[dict[str, object]] | None = None,
) -> None:
    try:
        outputs = budget_state.refresh_budget_state(
            db_path,
            budget_config,
            run_date,
            active_alarms=active_alarms,
            project_root=PROJECT_ROOT,
        )
    except Exception as exc:
        print(f"Warning: lockscreen refresh failed: {exc}")
        return

    if outputs["png_paths"]:
        print(f"Lockscreen assets refreshed: {outputs['png_paths'][0]}")
    if outputs["widget_paths"]:
        print(f"Widget snapshot refreshed: {outputs['widget_paths'][0]}")


def generate_sample_report(reports_root: Path, config: dict, report_date: date) -> Path:
    with tempfile.TemporaryDirectory(prefix="lunchmoney-sample-") as tmp:
        tmp_path = Path(tmp)
        sample_db = tmp_path / "sample.db"
        storage.seed_mock_data(sample_db, report_date)
        run_id, _ = rules.run_checks(sample_db, config, report_date)
        path = report.write_report(
            sample_db,
            reports_root,
            report_date,
            run_id=run_id,
            sample=True,
            max_flagged_transactions=int(config.get("report", {}).get("max_flagged_transactions", 40)),
        )
        sample_raw = tmp_path / "raw-sample"
        if sample_raw.exists():
            shutil.rmtree(sample_raw)
        return path


def write_alarm_outputs(
    db_path: Path,
    reports_root: Path,
    config: dict,
    budget_config: dict,
    run_date: date,
    *,
    notify: bool = False,
) -> tuple[Path, list[dict]]:
    run_id = storage.latest_rule_run_id(db_path, run_date)
    if run_id is None:
        run_id, _ = rules.run_checks(db_path, config, run_date)
    path, active_alarms = alarms.write_alarm_report(
        db_path,
        reports_root,
        run_id,
        run_date,
        budget_config,
    )
    if notify:
        alarms.send_local_notification(active_alarms, budget_config)
    return path, active_alarms


def generate_sample_alarms(
    reports_root: Path, config: dict, budget_config: dict, report_date: date
) -> Path:
    with tempfile.TemporaryDirectory(prefix="lunchmoney-sample-") as tmp:
        tmp_path = Path(tmp)
        sample_db = tmp_path / "sample.db"
        storage.seed_mock_data(sample_db, report_date)
        run_id, _ = rules.run_checks(sample_db, config, report_date)
        path, _ = alarms.write_alarm_report(
            sample_db,
            reports_root,
            run_id,
            report_date,
            budget_config,
            sample=True,
        )
        sample_raw = tmp_path / "raw-sample"
        if sample_raw.exists():
            shutil.rmtree(sample_raw)
        return path


def generate_sample_weekly_email(
    reports_root: Path, config: dict, budget_config: dict, report_date: date
) -> Path:
    with tempfile.TemporaryDirectory(prefix="lunchmoney-sample-") as tmp:
        tmp_path = Path(tmp)
        sample_db = tmp_path / "sample.db"
        storage.seed_mock_data(sample_db, report_date)
        run_id, _ = rules.run_checks(sample_db, config, report_date)
        path, _ = weekly_email.write_weekly_email(
            sample_db,
            reports_root,
            run_id,
            report_date,
            budget_config,
            sample=True,
        )
        sample_raw = tmp_path / "raw-sample"
        if sample_raw.exists():
            shutil.rmtree(sample_raw)
        return path


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _month_end(day: date) -> date:
    if day.month == 12:
        return date(day.year, 12, 31)
    return date(day.year, day.month + 1, 1) - timedelta(days=1)


if __name__ == "__main__":
    raise SystemExit(main())
