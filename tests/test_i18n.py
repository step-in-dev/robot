from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from robot import i18n


class I18nTest(unittest.TestCase):
    def tearDown(self) -> None:
        i18n.clear_translation_cache()

    def test_normalize_language_russian_variants(self) -> None:
        self.assertEqual(i18n.normalize_language("ru"), "ru")
        self.assertEqual(i18n.normalize_language("ru_RU.UTF-8"), "ru")
        self.assertEqual(i18n.normalize_language("ru-RU"), "ru")

    def test_normalize_language_english_variants(self) -> None:
        self.assertEqual(i18n.normalize_language("en"), "en")
        self.assertEqual(i18n.normalize_language("en-GB"), "en")
        self.assertEqual(i18n.normalize_language("en_US.UTF-8"), "en")

    def test_normalize_language_more_supported_variants(self) -> None:
        self.assertEqual(i18n.normalize_language("de_DE.UTF-8"), "de")
        self.assertEqual(i18n.normalize_language("zh_CN.UTF-8"), "zh")
        self.assertEqual(i18n.normalize_language("pt-BR"), "pt")
        self.assertEqual(i18n.normalize_language("uk_UA"), "uk")

    def test_normalize_language_unsupported_returns_none(self) -> None:
        self.assertIsNone(i18n.normalize_language("eo.UTF-8"))
        self.assertIsNone(i18n.normalize_language(""))
        self.assertIsNone(i18n.normalize_language("C"))

    def test_detect_language_respects_robot_language(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "ru"}, clear=False):
            self.assertEqual(i18n.detect_language(), "ru")
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False):
            self.assertEqual(i18n.detect_language(), "en")
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "de"}, clear=False):
            self.assertEqual(i18n.detect_language(), "de")

    def test_t_english_and_russian(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False):
            self.assertEqual(i18n.t("status.ready"), "Robot: Ready")
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "ru"}, clear=False):
            self.assertEqual(i18n.t("status.ready"), "Робот: Готов")

    def test_button_help_en_and_ru(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "en"}, clear=False):
            self.assertEqual(i18n.t("button.help"), "Help")
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "ru"}, clear=False):
            self.assertEqual(i18n.t("button.help"), "Справка")

    def test_t_german_and_chinese_smoke(self) -> None:
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "de"}, clear=False):
            self.assertEqual(i18n.t("status.ready"), "Roboter: Bereit")
        with patch.dict("os.environ", {"ROBOT_LANGUAGE": "zh"}, clear=False):
            self.assertEqual(i18n.t("status.ready"), "机器人：就绪")

    def test_locale_files_have_same_keys(self) -> None:
        base = Path(__file__).resolve().parent.parent / "robot" / "locales"
        with (base / "en.json").open(encoding="utf-8") as f_en:
            keys_en = set(json.load(f_en))
        for lang in i18n.SUPPORTED_LANGUAGES:
            with self.subTest(lang=lang):
                with (base / f"{lang}.json").open(encoding="utf-8") as f:
                    keys_lang = set(json.load(f))
                self.assertEqual(keys_en, keys_lang)

    def test_public_text_constants_are_plain_str(self) -> None:
        from robot import executor
        from robot import gui_theme
        from robot import operator_limits

        self.assertIsInstance(gui_theme.STATUS_READY, str)
        self.assertIsInstance(executor.ROBOT_PATH_COLLISION_USER_MESSAGE, str)
        self.assertIsInstance(executor.EXECUTION_CANCELLED_MESSAGE, str)
        self.assertIsInstance(operator_limits.OPERATORS_LIMIT_MESSAGE_TEMPLATE, str)


if __name__ == "__main__":
    unittest.main()
