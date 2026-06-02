from __future__ import annotations

import argparse
import os
import unittest
from unittest.mock import patch

from src.main import (
    ConfigurationValidationError,
    _command_requires_lunchmoney_token,
    _validate_startup_configuration,
)


class ConfigValidationTests(unittest.TestCase):
    def test_pull_requires_token(self) -> None:
        args = argparse.Namespace(command="pull")
        self.assertTrue(_command_requires_lunchmoney_token(args))

    def test_weekly_email_with_no_pull_skips_token_requirement(self) -> None:
        args = argparse.Namespace(command="weekly-email", no_pull=True)
        self.assertFalse(_command_requires_lunchmoney_token(args))

    def test_missing_token_reports_exact_env_var(self) -> None:
        args = argparse.Namespace(command="monitor")
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationValidationError) as exc:
                _validate_startup_configuration(args)
        self.assertIn("Missing required environment variable(s): LUNCHMONEY_ACCESS_TOKEN.", str(exc.exception))
        self.assertIn("README.md Quick Start.", str(exc.exception))

    def test_placeholder_token_is_rejected(self) -> None:
        args = argparse.Namespace(command="run-all")
        with patch.dict(
            os.environ,
            {"LUNCHMONEY_ACCESS_TOKEN": "replace_with_your_lunch_money_access_token"},
            clear=True,
        ):
            with self.assertRaises(ConfigurationValidationError) as exc:
                _validate_startup_configuration(args)
        self.assertIn("Invalid placeholder value for: LUNCHMONEY_ACCESS_TOKEN.", str(exc.exception))

    def test_valid_token_passes(self) -> None:
        args = argparse.Namespace(command="pull")
        with patch.dict(os.environ, {"LUNCHMONEY_ACCESS_TOKEN": "real_token_value"}, clear=True):
            _validate_startup_configuration(args)


if __name__ == "__main__":
    unittest.main()
