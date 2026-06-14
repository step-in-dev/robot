"""Tests for tk_util helpers."""

from __future__ import annotations

import sys
import unittest
from unittest import mock

from robot.tk_util import fix_win_hidpi


class FixWinHidpiTest(unittest.TestCase):
    def test_noop_off_windows(self) -> None:
        with mock.patch.object(sys, "platform", "linux"):
            fix_win_hidpi()

    def test_calls_set_process_dpi_awareness_on_windows(self) -> None:
        ole_dll = mock.Mock()
        with mock.patch.object(sys, "platform", "win32"), mock.patch(
            "robot.tk_util.ctypes.OleDLL", return_value=ole_dll, create=True
        ) as ole_dll_ctor:
            fix_win_hidpi()
        ole_dll_ctor.assert_called_once_with("shcore")
        ole_dll.SetProcessDpiAwareness.assert_called_once_with(1)

    def test_ignores_oserror_from_windows_api(self) -> None:
        ole_dll = mock.Mock()
        ole_dll.SetProcessDpiAwareness.side_effect = OSError()
        with mock.patch.object(sys, "platform", "win32"), mock.patch(
            "robot.tk_util.ctypes.OleDLL", return_value=ole_dll, create=True
        ):
            fix_win_hidpi()


if __name__ == "__main__":
    unittest.main()
