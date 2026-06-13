"""Static strings and URL constants for the Robot website generator."""

from __future__ import annotations

from typing import Dict, Tuple
from pathlib import Path

from robot.student_api import STUDENT_COMMAND_NAMES

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SITE_BASE = "https://robot.stepindev.com"
WEBSITE_DIR = PROJECT_ROOT / "website"
TASKS_IMG_DIR = WEBSITE_DIR / "img" / "tasks"
SUPPORTED_SITE_LANGS = ("en", "ru")

THEME_URL_SLUG: Dict[str, str] = {
    "intro": "intro",
    "fun": "functions",
    "for": "for-loop",
    "forfun": "for-and-functions",
    "w": "while",
    "wfun": "while-and-functions",
    "if": "if",
    "wif": "while-with-if",
    "ifelse": "if-else",
    "compound": "compound",
}

COMMAND_GROUPS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("task_field", ("task", "field")),
    ("movement", ("move_right", "move_left", "move_up", "move_down")),
    (
        "cell_walls",
        tuple(
            name
            for name in STUDENT_COMMAND_NAMES
            if name
            not in (
                "move_right",
                "move_left",
                "move_up",
                "move_down",
                "pol",
                "printn",
            )
        ),
    ),
    ("values", ("pol", "printn")),
)

UI_STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        "site_name": "Robot",
        "home": "Home",
        "task_catalog": "Task catalog",
        "command_reference": "Command reference",
        "get_started_nav": "Get started",
        "tasks_nav": "Task catalog",
        "commands_nav": "Command reference",
        "github": "GitHub",
        "skip": "Skip to content",
        "open_menu": "Open menu",
        "primary_nav": "Primary",
        "english": "English",
        "russian": "Русский",
        "footer_tagline": "Robot – educational simulator",
        "releases": "Releases",
        "environments_heading": "Environments",
        "environment_n": "Environment {n}",
        "env_view_full": "View environment {n} full size",
        "env_lightbox_close": "Close",
        "constraints_heading": "Constraints",
        "example_heading": "Example in Python",
        "prev_task": "Previous task",
        "next_task": "Next task",
        "catalog_intro": (
            "All bundled Robot tasks grouped by topic. Each page shows the task "
            "condition, field layouts, and limits."
        ),
        "commands_page_title": "Robot command reference (Python) | Robot",
        "commands_meta_description": (
            "Robot Python command reference: movement, painting, walls, cell values, "
            "task(), field(), pol(), and printn(), each with a short description."
        ),
        "commands_intro": (
            "Below are all commands available to students in the Robot simulator. "
            "Use {code} in your program, or import only the names you need."
        ),
        "commands_schema_name": "Robot Python command reference",
        "commands_og_image_alt": (
            "Robot command reference page listing move, paint, task(), "
            "and other student commands."
        ),
        "tasks_in_theme": "{count} tasks",
        "task_count_total": "{count} tasks in total",
        "theme_hub_meta_description": (
            "{count} Robot tasks on {theme}: {range}. "
            "Browse task conditions, field layouts, and limits."
        ),
        "theme_hub_og_image_alt": (
            "Robot tasks on {theme} ({range}): grid field previews from the task catalog."
        ),
        "og_default_alt": "Robot desktop window showing a grid programming task.",
        "articles_nav": "Articles",
        "articles_heading": "Articles",
        "articles_intro": (
            "Long-form guides about the Robot simulator for teachers and learners."
        ),
        "articles_empty": "No articles published yet.",
        "editor_nav": "Environment editor",
        "editor_intro": (
            "Step-by-step instructions for adding custom Robot tasks with the "
            "online environment editor."
        ),
        "editor_step_1": "Open the {link}.",
        "editor_step_2": "Create as many environments as the task needs.",
        "editor_step_3": (
            "Save the environments to a file. In the save dialog, choose Environment "
            "and enter a file name ending in .env."
        ),
        "editor_step_4": "Copy the .env file to the robot/tasks folder of the robot package.",
        "editor_step_5": (
            "In your Python program, call task() with the file name without the .env extension."
        ),
        "editor_note_heading": "Note",
        "editor_note_p1": (
            "The editor saves task conditions (todoText) as a plain string, or edits one "
            "locale at a time when the file already contains localized text. To manage "
            "every translation, edit the file manually."
        ),
        "editor_note_p2": (
            "The editor does not support constraints such as operator limits, custom "
            "function call counts, or required or banned keywords. Add these fields "
            "manually following the {link}."
        ),
        "editor_format_link": "solution constraints documentation",
        "editor_online_editor": "online environment editor",
        "editor_fig_editor": "Environment editor.",
        "editor_fig_save": "Save environments dialog.",
        "editor_example_task": "robot",
    },
    "ru": {
        "site_name": "Робот",
        "home": "Главная",
        "task_catalog": "Каталог задач",
        "command_reference": "Справочник команд",
        "get_started_nav": "Как начать",
        "tasks_nav": "Каталог задач",
        "commands_nav": "Справочник команд",
        "github": "GitHub",
        "skip": "Перейти к содержанию",
        "open_menu": "Открыть меню",
        "primary_nav": "Основная навигация",
        "english": "English",
        "russian": "Русский",
        "footer_tagline": "Робот – учебный исполнитель",
        "releases": "Релизы",
        "environments_heading": "Обстановки",
        "environment_n": "Обстановка {n}",
        "env_view_full": "Открыть обстановку {n} в полном размере",
        "env_lightbox_close": "Закрыть",
        "constraints_heading": "Ограничения",
        "example_heading": "Пример на Python",
        "prev_task": "Предыдущая задача",
        "next_task": "Следующая задача",
        "catalog_intro": (
            "Все встроенные задачи Робота по темам. На странице задачи – условие, "
            "поля обстановок и ограничения."
        ),
        "commands_page_title": "Справочник команд Робота на Python | Robot",
        "commands_meta_description": (
            "Справочник команд исполнителя Робот на Python: движение, закраска, "
            "проверка стен и клеток, task(), field(), pol() и printn()."
        ),
        "commands_intro": (
            "Ниже — все команды, доступные учащимся в исполнителе Робот. "
            "В программе подключите модуль: {code} или импортируйте только нужные имена."
        ),
        "commands_schema_name": "Справочник команд Робота на Python",
        "commands_og_image_alt": (
            "Справочник команд исполнителя Робот: сигнатуры и описания move, paint, "
            "task() и других команд."
        ),
        "tasks_in_theme": "Задач: {count}",
        "task_count_total": "Всего задач: {count}",
        "theme_hub_meta_description": (
            "{count} задач Робота по теме «{theme}»: {range}. "
            "Условия, поля обстановок и ограничения."
        ),
        "theme_hub_og_image_alt": (
            "Задачи Робота по теме «{theme}» ({range}): превью полей из каталога задач."
        ),
        "og_default_alt": "Окно Робота с задачей на клеточном поле.",
        "articles_nav": "Статьи",
        "articles_heading": "Статьи",
        "articles_intro": (
            "Подробные материалы об исполнителе Робот для учителей и учащихся."
        ),
        "articles_empty": "Пока нет опубликованных статей.",
        "editor_nav": "Редактор обстановок",
        "editor_intro": (
            "Пошаговая инструкция по добавлению своих задач для исполнителя Робот "
            "с помощью онлайн-редактора обстановок."
        ),
        "editor_step_1": "Откройте {link}.",
        "editor_step_2": "Создайте нужное количество обстановок для задачи.",
        "editor_step_3": (
            "Сохраните обстановки в файл. В диалоге сохранения выберите «Обстановка» "
            "и укажите имя файла с расширением .env."
        ),
        "editor_step_4": "Скопируйте файл .env в папку robot/tasks модуля robot.",
        "editor_step_5": (
            "В программе на Python вызовите task() с именем файла без расширения .env."
        ),
        "editor_note_heading": "Замечание",
        "editor_note_p1": (
            "Редактор сохраняет условие задачи (todoText) одной строкой или редактирует "
            "одну локаль за раз, если в файле уже есть переводы. Чтобы изменить все "
            "переводы сразу, отредактируйте файл вручную."
        ),
        "editor_note_p2": (
            "Редактор не поддерживает ограничения: лимит действий Робота, число вызовов "
            "своих функций, обязательные и запрещённые ключевые слова и т.п. Добавьте "
            "такие поля вручную по {link}."
        ),
        "editor_format_link": "описанию ограничений",
        "editor_online_editor": "онлайн-редактор обстановок",
        "editor_fig_editor": "Редактор обстановок.",
        "editor_fig_save": "Диалог сохранения обстановки.",
        "editor_example_task": "robot",
    },
}

EDITOR_PAGE_URL = {
    "en": "https://stepindev.com/en/py-robot",
    "ru": "https://stepindev.com/ru/py-robot",
}
_RU_CONSTRAINTS_ANCHOR = (
    "%D0%BE%D0%B3%D1%80%D0%B0%D0%BD%D0%B8%D1%87%D0%B5%D0%BD%D0%B8%D1%8F-"
    "%D0%BD%D0%B0-%D1%80%D0%B5%D1%88%D0%B5%D0%BD%D0%B8%D0%B5"
)
ENV_FORMAT_DOC_URL = {
    "en": (
        "https://github.com/step-in-dev/robot/blob/main/"
        "Docs/task-env-format.md#solution-constraints"
    ),
    "ru": (
        "https://github.com/step-in-dev/robot/blob/main/"
        f"Docs/task-env-format.ru.md#{_RU_CONSTRAINTS_ANCHOR}"
    ),
}

COMMAND_GROUP_TITLES: Dict[str, Dict[str, str]] = {
    "en": {
        "task_field": "Task or free field",
        "movement": "Movement",
        "cell_walls": "Cell & walls",
        "values": "Values & output",
    },
    "ru": {
        "task_field": "Задача или свободное поле",
        "movement": "Движение",
        "cell_walls": "Клетка и стены",
        "values": "Значения и вывод",
    },
}

COMMAND_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "en": (
        "robot simulator commands",
        "robot python API",
        "move_right robot",
        "task() robot",
        "robot command reference",
        "grid robot programming",
    ),
    "ru": (
        "исполнитель робот команды",
        "робот python команды",
        "move_right робот",
        "task робот",
        "справочник команд робот",
        "paint робот",
    ),
}

THEME_HUB_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "en": (
        "robot tasks",
        "python programming",
        "grid robot simulator",
        "educational programming",
    ),
    "ru": (
        "задачи робот",
        "python программирование",
        "исполнитель робот",
        "учебное программирование",
    ),
}
