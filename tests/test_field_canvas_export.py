"""Tests for exporting the field grid canvas to PNG."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.env_fixtures import env_dict, make_env
from tests.gui._helpers import (
    GuiTestCase,
    make_test_window,
    requires_tk_display,
)
from tools.field_canvas_export import write_robot_window_field_canvas


@requires_tk_display
class FieldCanvasExportTests(GuiTestCase):
    def test_export_field_canvas_writes_png(self) -> None:
        env = make_env(env_dict(4, 2, final_col=0, final_row=0))
        window = make_test_window("if3", [env], None)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "field.png"
                write_robot_window_field_canvas(window, path)
                self.assertTrue(path.is_file())
                header = path.read_bytes()[:8]
                self.assertEqual(header, b"\x89PNG\r\n\x1a\n")
        finally:
            window.close()

if __name__ == "__main__":
    unittest.main()
