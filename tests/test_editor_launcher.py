"""Tests for the environment editor launcher."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import List
from unittest.mock import patch
from editor import editor

from robot.task_serializer import EditorDocument, create_empty_document


class EditorLauncherTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        repo_root_str = str(repo_root)
        if repo_root_str not in sys.path:
            sys.path.insert(0, repo_root_str)

    def test_main_opens_editor_with_empty_document(self) -> None:

        captured: List[EditorDocument] = []

        class CaptureEditorWindow:
            def __init__(self, document=None):
                captured.append(document or create_empty_document())

            def run(self) -> None:
                pass

        with patch("editor.editor.EditorWindow", CaptureEditorWindow):
            exit_code = editor.main()
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(captured), 1)
        self.assertEqual(len(captured[0].env_dtos), 1)
        self.assertIsNone(captured[0].file_path)


if __name__ == "__main__":
    unittest.main()
