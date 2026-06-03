from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src import budget_state, storage


class V1PipelineTests(unittest.TestCase):
    def test_refresh_writes_budget_state_json_and_lockscreen_from_config(self) -> None:
        run_date = date(2026, 6, 3)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db_path = root / "lunchmoney.db"
            _seed_pipeline_db(db_path, run_date)

            outputs = budget_state.refresh_budget_state(
                db_path,
                _budget_config(daily_allowance=55),
                run_date,
                active_alarms=[],
                project_root=root,
            )

            json_path = (root / "data" / "budget_state.json").resolve()
            png_path = (root / "data" / "lockscreen_latest.png").resolve()
            self.assertTrue(json_path.exists())
            self.assertTrue(png_path.exists())
            payload = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertIn(json_path, outputs["json_paths"])
        self.assertIn(png_path, outputs["png_paths"])
        self.assertEqual(payload["daily_allowance"], 55)
        self.assertEqual(payload["today_discretionary_spend"], 18)
        self.assertEqual(payload["remaining_today"], 37)
        self.assertFalse(payload["is_negative"])
        self.assertEqual(payload["excluded_categories"], ["Transfers", "Utilities"])
        self.assertEqual(payload["excluded_payees"], ["Ignored Store"])

    def test_daily_allowance_change_updates_remaining_today(self) -> None:
        run_date = date(2026, 6, 3)
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "lunchmoney.db"
            _seed_pipeline_db(db_path, run_date)

            first = budget_state.build_budget_state_payload(
                db_path,
                _budget_config(daily_allowance=55),
                run_date,
                active_alarms=[],
            )
            second = budget_state.build_budget_state_payload(
                db_path,
                _budget_config(daily_allowance=111),
                run_date,
                active_alarms=[],
            )

        self.assertEqual(first["remaining_today"], 37)
        self.assertEqual(second["remaining_today"], 93)

    def test_excluded_categories_and_payees_do_not_count_against_spend(self) -> None:
        run_date = date(2026, 6, 3)
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "lunchmoney.db"
            _seed_pipeline_db(db_path, run_date)

            with_exclusions = budget_state.build_budget_state_payload(
                db_path,
                _budget_config(daily_allowance=55),
                run_date,
                active_alarms=[],
            )
            without_exclusions = budget_state.build_budget_state_payload(
                db_path,
                _budget_config(
                    daily_allowance=55,
                    excluded_categories=["No Matching Category"],
                    excluded_payees=["No Matching Payee"],
                ),
                run_date,
                active_alarms=[],
            )

        self.assertEqual(with_exclusions["today_discretionary_spend"], 18)
        self.assertEqual(without_exclusions["today_discretionary_spend"], 140)
        self.assertEqual(without_exclusions["remaining_today"], -85)
        self.assertTrue(without_exclusions["is_negative"])


def _budget_config(
    *,
    daily_allowance: int,
    excluded_categories: list[str] | None = None,
    excluded_payees: list[str] | None = None,
) -> dict:
    return {
        "budget": {
            "cash_buffer": {"enabled": False},
            "discretionary_total": {"enabled": True, "monthly_limit": 900},
            "categories": [
                {"name": "Restaurants", "discretionary": True},
                {"name": "Transfers", "discretionary": False},
                {"name": "Utilities", "discretionary": False},
            ],
        },
        "one_number": {
            "daily_allowance": daily_allowance,
            "excluded_categories": excluded_categories
            if excluded_categories is not None
            else ["Transfers", "Utilities"],
            "excluded_payees": excluded_payees
            if excluded_payees is not None
            else ["Ignored Store"],
            "reset_day": 1,
            "reset_time": "00:00",
        },
        "lockscreen": {
            "weekly_spend_days": 5,
            "dopamine_ratio_of_today": 0.85,
            "dopamine_daily_cap": 35,
        },
    }


def _seed_pipeline_db(db_path: Path, run_date: date) -> None:
    storage.init_db(db_path)
    storage.save_pull_snapshot(
        db_path,
        db_path.parent / "raw",
        run_date,
        {
            "categories": {
                "categories": [
                    {"id": 1, "name": "Restaurants", "is_income": False},
                    {"id": 2, "name": "Transfers", "is_income": False},
                    {"id": 3, "name": "Utilities", "is_income": False},
                ]
            },
            "transactions": {
                "transactions": [
                    {
                        "id": 1,
                        "date": run_date.isoformat(),
                        "amount": "18.00",
                        "payee": "Lunch Place",
                        "category_id": 1,
                        "status": "reviewed",
                        "is_pending": False,
                    },
                    {
                        "id": 2,
                        "date": run_date.isoformat(),
                        "amount": "100.00",
                        "payee": "Bank Transfer",
                        "category_id": 2,
                        "status": "reviewed",
                        "is_pending": False,
                    },
                    {
                        "id": 3,
                        "date": run_date.isoformat(),
                        "amount": "22.00",
                        "payee": "Ignored Store",
                        "category_id": 1,
                        "status": "reviewed",
                        "is_pending": False,
                    },
                ]
            },
            "manual_accounts": {"manual_accounts": []},
            "plaid_accounts": {"plaid_accounts": []},
            "recurring_items": {"recurring_items": []},
            "budget_summary": {"categories": []},
        },
    )


if __name__ == "__main__":
    unittest.main()
