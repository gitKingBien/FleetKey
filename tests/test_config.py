"""Core config and geometry tests for FleetKey."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app


class ConfigTests(unittest.TestCase):
    def test_parse_geometry_valid(self) -> None:
        parsed = app.parse_geometry("340x420+60+60")
        self.assertEqual(parsed, (340, 420, 60, 60))

    def test_parse_geometry_invalid(self) -> None:
        self.assertIsNone(app.parse_geometry("bad-value"))

    def test_normalize_geometry_fallback(self) -> None:
        normalized = app.normalize_geometry(
            "invalid",
            app.DEFAULT_GEOMETRY,
            min_width=app.MIN_WIDTH,
            min_height=app.MIN_EXPANDED_HEIGHT,
        )
        self.assertEqual(normalized, app.DEFAULT_GEOMETRY)

    def test_normalize_collapsed_geometry_fixed_height(self) -> None:
        normalized = app.normalize_collapsed_geometry(
            "300x999+10+20",
            app.DEFAULT_COLLAPSED_GEOMETRY,
        )
        self.assertEqual(normalized, "300x56+10+20")

    def test_sanitize_config_with_bad_values(self) -> None:
        bad_data = {
            "opacity": "high",
            "geometry": "bad",
            "expanded_geometry": "bad",
            "collapsed_geometry": "bad",
            "is_collapsed": "truthy",
            "shortcuts": [{"label": "  Docs  ", "target": "  C:\\Docs  "}],
        }
        sanitized = app.sanitize_config(bad_data)
        self.assertEqual(sanitized["opacity"], app.DEFAULT_CONFIG["opacity"])
        self.assertEqual(
            sanitized["expanded_geometry"],
            app.DEFAULT_GEOMETRY,
        )
        self.assertEqual(
            sanitized["collapsed_geometry"],
            app.DEFAULT_COLLAPSED_GEOMETRY,
        )
        self.assertTrue(sanitized["is_collapsed"])
        self.assertEqual(
            sanitized["shortcuts"],
            [{"label": "Docs", "target": "C:\\Docs"}],
        )

    def test_load_config_accepts_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "shortcuts.json"
            payload = {
                "opacity": 0.7,
                "geometry": "340x420+60+60",
                "shortcuts": [{"label": "Docs", "target": "C:\\Docs"}],
            }
            config_path.write_text(
                json.dumps(payload),
                encoding="utf-8-sig",
            )

            with patch.object(app, "CONFIG_PATH", config_path):
                loaded = app.load_config()

        self.assertEqual(loaded["opacity"], 0.7)
        self.assertEqual(
            loaded["shortcuts"],
            [{"label": "Docs", "target": "C:\\Docs"}],
        )

    def test_load_config_can_keep_fallback_state_on_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "shortcuts.json"
            config_path.write_text(
                '{"shortcuts":[{"label":"Bad","target":"C:\\new\\path"}]}',
                encoding="utf-8",
            )
            fallback = {
                "opacity": 0.8,
                "geometry": app.DEFAULT_GEOMETRY,
                "expanded_geometry": app.DEFAULT_GEOMETRY,
                "collapsed_geometry": app.DEFAULT_COLLAPSED_GEOMETRY,
                "is_collapsed": False,
                "shortcuts": [{"label": "Keep", "target": "https://example.com"}],
            }

            with (
                patch.object(app, "CONFIG_PATH", config_path),
                patch.object(app.messagebox, "showwarning"),
            ):
                loaded = app.load_config(fallback_on_error=fallback)

        self.assertEqual(
            loaded["shortcuts"],
            [{"label": "Keep", "target": "https://example.com"}],
        )


if __name__ == "__main__":
    unittest.main()
