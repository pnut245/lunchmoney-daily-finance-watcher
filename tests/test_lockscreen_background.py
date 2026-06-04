from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src import budget_state, lockscreen, wallpaper

REPO_ROOT = Path(__file__).resolve().parents[1]


class LockscreenCliTests(unittest.TestCase):
    def test_render_lockscreen_returns_expected_size_for_adhd_payload(self) -> None:
        image = lockscreen.render_lockscreen(
            {
                "safe_to_spend": "$42",
                "spending_state": "COMFORTABLE",
                "money_object": "Dinner Plate",
                "today": "$42",
                "week": "$210",
                "dopamine": "$35",
            }
        )

        self.assertEqual(image.size, (lockscreen.WIDTH, lockscreen.HEIGHT))

    def test_main_writes_png_from_json_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "budget_state.json"
            output_path = tmp_path / "lockscreen.png"
            input_path.write_text(
                json.dumps(
                    {
                        "safe_to_spend": "$42",
                        "spending_state": "COMFORTABLE",
                        "money_object": "Dinner Plate",
                        "today": "$42",
                        "week": "$210",
                        "dopamine": "$35",
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = lockscreen.main([str(input_path), str(output_path)])

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("Rendered lockscreen to", stdout.getvalue())

    def test_main_returns_error_for_missing_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            missing_path = tmp_path / "missing.json"
            output_path = tmp_path / "lockscreen.png"
            stderr = io.StringIO()

            with contextlib.redirect_stderr(stderr):
                exit_code = lockscreen.main([str(missing_path), str(output_path)])

            self.assertEqual(exit_code, 1)
            self.assertIn("Missing input JSON", stderr.getvalue())


class BudgetStateRefreshTests(unittest.TestCase):
    def test_refresh_budget_state_writes_project_and_runtime_outputs(self) -> None:
        payload = {
            "safe_to_spend": "$42",
            "spending_state": "COMFORTABLE",
            "money_object": "Dinner Plate",
            "today": "$42",
            "week": "$210",
            "dopamine": "$35",
        }

        with tempfile.TemporaryDirectory() as project_tmpdir, tempfile.TemporaryDirectory() as runtime_tmpdir:
            project_root = Path(project_tmpdir)
            runtime_dir = Path(runtime_tmpdir)

            with (
                patch("src.budget_state.build_budget_state_payload", return_value=payload),
                patch.object(budget_state, "RUNTIME_DIR", runtime_dir),
                patch("src.budget_state.lockscreen.render_lockscreen", return_value=Image.new("RGBA", (12, 12))),
            ):
                result = budget_state.refresh_budget_state(
                    Path("/tmp/fake.db"),
                    budget_config={},
                    run_date=__import__("datetime").date(2026, 6, 2),
                    project_root=project_root,
                )

            expected_json_paths = {
                (project_root / "data" / "budget_state.json").resolve(),
                (runtime_dir / "budget_state.json").resolve(),
            }
            expected_png_paths = {
                (project_root / "data" / "lockscreen_latest.png").resolve(),
                (runtime_dir / "lockscreen_latest.png").resolve(),
            }

            self.assertEqual(set(result["json_paths"]), expected_json_paths)
            self.assertEqual(set(result["png_paths"]), expected_png_paths)

            for json_path in expected_json_paths:
                self.assertTrue(json_path.exists())
                self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), payload)

            for png_path in expected_png_paths:
                self.assertTrue(png_path.exists())

    def test_output_roots_skips_missing_runtime_dir(self) -> None:
        with tempfile.TemporaryDirectory() as project_tmpdir, tempfile.TemporaryDirectory() as runtime_tmpdir:
            project_root = Path(project_tmpdir)
            runtime_dir = Path(runtime_tmpdir) / "missing-runtime"

            with patch.object(budget_state, "RUNTIME_DIR", runtime_dir):
                roots = budget_state._output_roots(project_root)

            self.assertEqual(roots, [(project_root / "data").resolve()])


class LockscreenRefreshScriptTests(unittest.TestCase):
    def test_refresh_script_renders_png_to_explicit_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "budget_state.json"
            output_path = tmp_path / "nested" / "lockscreen.png"
            input_path.write_text(
                json.dumps(
                    {
                        "safe_to_spend": "$42",
                        "spending_state": "COMFORTABLE",
                        "money_object": "Dinner Plate",
                        "today": "$42",
                        "week": "$210",
                        "dopamine": "$35",
                    }
                ),
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["BUDGET_STATE_PATH"] = str(input_path)
            env["LOCKSCREEN_OUTPUT_PATH"] = str(output_path)
            env["LOCKSCREEN_WALLPAPER_NOOP"] = "1"

            result = subprocess.run(
                [str(REPO_ROOT / "run_lockscreen_refresh.sh")],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(output_path.exists())
            self.assertIn("Rendered lockscreen to", result.stdout)
            self.assertIn("Applied wallpaper from", result.stdout)

    def test_refresh_script_can_skip_wallpaper_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "budget_state.json"
            output_path = tmp_path / "nested" / "lockscreen.png"
            input_path.write_text(
                json.dumps(
                    {
                        "safe_to_spend": "$42",
                        "spending_state": "COMFORTABLE",
                        "money_object": "Dinner Plate",
                        "today": "$42",
                        "week": "$210",
                        "dopamine": "$35",
                    }
                ),
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["BUDGET_STATE_PATH"] = str(input_path)
            env["LOCKSCREEN_OUTPUT_PATH"] = str(output_path)
            env["LOCKSCREEN_APPLY_WALLPAPER"] = "0"

            result = subprocess.run(
                [str(REPO_ROOT / "run_lockscreen_refresh.sh")],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(output_path.exists())
            self.assertIn("Rendered lockscreen to", result.stdout)
            self.assertNotIn("Applied wallpaper from", result.stdout)


class WallpaperApplyTests(unittest.TestCase):
    def test_apply_wallpaper_uses_fallback_script_when_finder_fails(self) -> None:
        image_path = Path("/tmp/test image.png")
        calls: list[list[str]] = []

        def fake_run(cmd: list[str], check: bool, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
            calls.append(cmd)
            if len(calls) == 1:
                raise subprocess.CalledProcessError(1, cmd, stderr="finder failed")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch("src.wallpaper.subprocess.run", side_effect=fake_run):
            wallpaper.apply_wallpaper(image_path)

        self.assertEqual(len(calls), 2)
        self.assertIn('tell application "Finder"', calls[0][2])
        self.assertIn('tell application "System Events"', calls[1][2])

    def test_apply_wallpaper_noops_when_override_is_enabled(self) -> None:
        image_path = Path("/tmp/test image.png")
        with (
            patch.dict(os.environ, {"LOCKSCREEN_WALLPAPER_NOOP": "1"}, clear=False),
            patch("src.wallpaper.subprocess.run") as mock_run,
        ):
            wallpaper.apply_wallpaper(image_path)

        mock_run.assert_not_called()

    def test_main_returns_error_for_missing_image(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            exit_code = wallpaper.main(["/tmp/does-not-exist.png"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Missing wallpaper image", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
