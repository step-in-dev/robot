"""Static strings and URL constants for the Robot website generator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from robot.student_api import ACTION_COMMAND_NAMES, ENVIRONMENT_QUERY_NAMES

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SITE_BASE = "https://robot.stepindev.com"
GITHUB_RELEASES_URL = "https://github.com/step-in-dev/robot/releases"
GITHUB_LATEST_DOWNLOAD_BASE = (
    "https://github.com/step-in-dev/robot/releases/latest/download"
)


def community_pack_download_url(zip_name: str) -> str:
    """Return a direct download URL for one community pack release archive."""
    return f"{GITHUB_LATEST_DOWNLOAD_BASE}/{zip_name}"
ONLINE_EDITOR_URL = {
    "en": "https://stepindev.com/en/py-robot",
    "ru": "https://stepindev.com/ru/py-robot",
}
ONLINE_EDITOR_MAX_ROWS = 8
ONLINE_EDITOR_MAX_COLS = 10
WEBSITE_DIR = PROJECT_ROOT / "website"
TASKS_IMG_DIR = WEBSITE_DIR / "img" / "tasks"
SUPPORTED_SITE_LANGS = ("en", "ru")


@dataclass(frozen=True)
class SitemapUrlGroup:
    """One or two localized paths for a sitemap alternate group."""

    en: Optional[str] = None
    ru: Optional[str] = None


FIELD_LEGEND_IMAGE = "img/commands/field.webp"
FIELD_LEGEND_WIDTH = 414
FIELD_LEGEND_HEIGHT = 413
FIELD_LEGEND_PADDING: Dict[str, int] = {
    "top": 56,
    "right": 220,
    "bottom": 72,
    "left": 140,
}
FIELD_LEGEND_LABEL_GAP = 28
FIELD_LEGEND_LINE_CLASS = "field-legend__leader"
FIELD_LEGEND_TEXT_CLASS = "field-legend__label"

_FIELD_LEGEND_GRID_ORIGIN = 5
_FIELD_LEGEND_CELL_SIZE = 80
_FIELD_LEGEND_CELL_CENTER_OFFSET = _FIELD_LEGEND_CELL_SIZE // 2


@dataclass(frozen=True)
class FieldLegendItem:
    """One labeled element on the commands-page field legend diagram."""

    item_id: str
    ax: int
    ay: int
    side: str
    label_dx: int = 0
    label_dy: int = 0
    connector_dy: int = 0


def _field_cell_center(col: int, row: int) -> Tuple[int, int]:
    """Return the pixel-space center of one field cell in field.webp."""
    x = (
        _FIELD_LEGEND_GRID_ORIGIN
        + col * _FIELD_LEGEND_CELL_SIZE
        + _FIELD_LEGEND_CELL_CENTER_OFFSET
    )
    y = (
        _FIELD_LEGEND_GRID_ORIGIN
        + row * _FIELD_LEGEND_CELL_SIZE
        + _FIELD_LEGEND_CELL_CENTER_OFFSET
    )
    return x, y


def _field_horizontal_wall_point(col: int, row_boundary: int) -> Tuple[int, int]:
    """Return a point on a horizontal wall segment between two rows."""
    return (
        _FIELD_LEGEND_GRID_ORIGIN
        + col * _FIELD_LEGEND_CELL_SIZE
        + _FIELD_LEGEND_CELL_CENTER_OFFSET,
        _FIELD_LEGEND_GRID_ORIGIN + row_boundary * _FIELD_LEGEND_CELL_SIZE,
    )


# Anchor coordinates are derived from the current 5x5 demo field image.
FIELD_LEGEND_ITEMS: Tuple[FieldLegendItem, ...] = (
    FieldLegendItem("robot", *_field_cell_center(0, 0), "left"),
    FieldLegendItem(
        "painted",
        *_field_cell_center(2, 0),
        "top",
        label_dx=-84,
        label_dy=12,
    ),
    FieldLegendItem("print", *_field_cell_center(2, 1), "right"),
    FieldLegendItem("pollution", *_field_cell_center(2, 2), "right"),
    FieldLegendItem(
        "to_paint",
        *_field_cell_center(2, 4),
        "bottom",
        label_dx=96,
        label_dy=-18,
    ),
    FieldLegendItem("walls", *_field_horizontal_wall_point(2, 2), "left", label_dy=22),
    FieldLegendItem("home", *_field_cell_center(4, 4), "right"),
)

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
    ("movement", ACTION_COMMAND_NAMES),
    ("cell_walls", ENVIRONMENT_QUERY_NAMES),
)

_RU_ARTICLES_LABEL = "Статьи"

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
        "brand_title_suffix": "Robot simulator in Python",
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
            "Bundled Robot tasks grouped by topic, plus community task packs "
            "published separately."
        ),
        "community_tasks_heading": "Community tasks",
        "community_pack_heading": "Task set {number}. Prepared by: {author}",
        "community_pack_download": (
            "Tasks in this section are not included in the module archive and are "
            "downloaded separately. Download tasks: {link}. Unpack into robot/tasks"
        ),
        "community_theme_hub_intro": (
            "Community tasks on {theme} collected in this pack."
        ),
        "commands_page_title": "Robot command reference",
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
        "commands_field_legend_title": "Task environment field elements",
        "commands_field_legend_robot": "Robot",
        "commands_field_legend_home": "Expected final\nposition of Robot",
        "commands_field_legend_painted": "Painted cell",
        "commands_field_legend_to_paint": "Marked cell",
        "commands_field_legend_walls": "Walls",
        "commands_field_legend_pollution": "Pollution level",
        "commands_field_legend_print": "Expected number (printn)",
        "commands_field_legend_completion": (
            "A task is considered complete if, after the program finishes, Robot is "
            "in the home cell, all cells marked for painting are painted, and the "
            "expected number has been printed in every cell that expects number output."
        ),
        "tasks_in_theme": "{count} tasks",
        "task_count_total": "{count} tasks in total",
        "theme_hub_meta_description": (
            "{count} Robot tasks in Python on {theme}: {range}. "
            "Browse task conditions, field layouts, and limits."
        ),
        "theme_hub_og_image_alt": (
            "Robot tasks on {theme} ({range}): grid field previews from the task catalog."
        ),
        "theme_hub_intro.intro": (
            "First steps with the Robot: move across a field, paint cells, and reach the "
            "goal cell. These tasks introduce the Robot and teach composing command "
            "sequences before students move on to loops and conditions."
        ),
        "theme_hub_intro.fun": (
            "Functions let students reuse a group of Robot commands instead of repeating "
            "them. These tasks teach how to define a custom function and call it, so "
            "solutions stay short and readable as the field grows."
        ),
        "theme_hub_intro.for": (
            "A 'for' loop repeats Robot commands a known number of times. A first "
            "introduction to counted loops."
        ),
        "theme_hub_intro.forfun": (
            "Combine a 'for' loop with user-defined functions to keep Robot solutions "
            "structured. These tasks ask students to wrap a repeated action in a "
            "function and call it inside a loop."
        ),
        "theme_hub_intro.w": (
            "A 'while' loop repeats Robot commands as long as a condition holds, which "
            "is useful when the number of steps is unknown. These tasks cover moving "
            "until a wall appears or a target cell is reached – the core of grid "
            "navigation with conditions."
        ),
        "theme_hub_intro.wfun": (
            "Pair a 'while' loop with user-defined functions to structure Robot "
            "solutions that run until a condition changes. These tasks teach students "
            "to extract a repeated check into a function and call it from a loop."
        ),
        "theme_hub_intro.if": (
            "An 'if' statement lets the Robot act differently depending on the field. "
            "These tasks introduce conditional execution without a loop."
        ),
        "theme_hub_intro.wif": (
            "A 'while' loop with an 'if' statement lets you solve more interesting "
            "tasks with the Robot."
        ),
        "theme_hub_intro.ifelse": (
            "An 'if' and 'else' pair lets a program for the Robot choose between "
            "two actions based on the field. These tasks teach branching with an "
            "alternative. For example, turn left or right depending on which side "
            "is free."
        ),
        "theme_hub_intro.compound": (
            "Compound conditions combine several checks with 'and' or 'or'. These "
            "tasks teach building logical expressions with the Robot environment "
            "analysis commands."
        ),
        "og_default_alt": "Robot desktop window showing a grid programming task.",
        "articles_nav": "Articles",
        "articles_heading": "Articles",
        "articles_page_title": "Articles",
        "articles_intro": (
            "Long-form guides about the Robot simulator for teachers and learners."
        ),
        "articles_empty": "No articles published yet.",
        "editor_nav": "Environment editor",
        "editor_intro": (
            "Step-by-step instructions for creating custom Robot tasks with the "
            "built-in environment editor."
        ),
        "editor_step_1": (
            "The environment editor is in editor/editor.py. Download the module archive "
            "from {link} and from the unpacked archive run:"
        ),
        "editor_step_2": "Create as many environments as the task needs.",
        "editor_step_3": "Save the task file to the robot/tasks folder.",
        "editor_step_4": (
            "In your Python program, call task() with the file name without the .env extension."
        ),
        "editor_note_heading": "Note",
        "editor_note_p1": (
            "The editor saves task conditions (todoText) as a plain string, or edits one "
            "locale at a time when the file already contains localized text. To manage "
            "every translation, edit the file manually."
        ),
        "editor_note_p2_intro": (
            "The editor can set solution constraints (toolbar constraints button):"
        ),
        "editor_fig_editor": "Environment editor.",
        "editor_example_task": "robot",
        "editor_online_heading": "Online environment editor",
        "editor_online_text": (
            "Create and edit task environments in the browser without installing "
            "the module."
        ),
        "editor_online_link": "Open online editor",
        "editor_online_limit_size": (
            "Supports smaller environments: up to {rows} rows by {cols} columns."
        ),
        "editor_online_limit_constraints": (
            "Does not support setting solution constraints."
        ),
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
        "brand_title_suffix": "Исполнитель Робот на Python",
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
            "Встроенные задачи исполнителя Робот по темам, а также отдельные наборы "
            "задач от сообщества."
        ),
        "community_tasks_heading": "Задачи от сообщества",
        "community_pack_heading": "Набор задач {number}. Подготовил: {author}",
        "community_pack_download": (
            "Задачи этого раздела не включены в архив с модулем и скачиваются отдельно. "
            "Скачать задачи: {link}. Распаковать в robot/tasks"
        ),
        "community_theme_hub_intro": (
            "Задачи от сообщества по теме «{theme}» из этого набора."
        ),
        "commands_page_title": "Справочник команд Робота",
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
        "commands_field_legend_title": "Элементы обстановки на поле",
        "commands_field_legend_robot": "Робот",
        "commands_field_legend_home": "Ожидаемое\nконечное положение Робота",
        "commands_field_legend_painted": "Закрашенная клетка",
        "commands_field_legend_to_paint": "Клетка, помеченная\nдля закраски",
        "commands_field_legend_walls": "Стены",
        "commands_field_legend_pollution": "Уровень загрязнения",
        "commands_field_legend_print": "Ожидаемое число (printn)",
        "commands_field_legend_completion": (
            "Задание считается выполненным, если после завершения работы программы "
            "исполнитель Робот находится в клетке с домиком, все помеченные для "
            "закраски клетки закрашены и во все клетки, ожидающие вывода числа, "
            "это число выведено."
        ),
        "tasks_in_theme": "Задач: {count}",
        "task_count_total": "Всего задач: {count}",
        "theme_hub_meta_description": (
            "{count} задач исполнителя Робот на Python по теме «{theme}»: {range}. "
            "Условия, поля обстановок и ограничения."
        ),
        "theme_hub_og_image_alt": (
            "Задачи исполнителя Робот по теме «{theme}» ({range}): превью полей из "
            "каталога задач."
        ),
        "theme_hub_intro.intro": (
            "Первые шаги с исполнителем Робот: перемещение по полю, закраска клеток и "
            "достижение целевой клетки. Задачи знакомят с исполнителем Робот и учат "
            "составлять последовательности команд перед переходом к циклам и условиям."
        ),
        "theme_hub_intro.fun": (
            "Функции позволяют повторно использовать группу команд исполнителя Робот "
            "вместо их повторения. Задачи учат определять собственную функцию и "
            "вызывать её, чтобы решения оставались короткими и понятными даже на "
            "больших полях."
        ),
        "theme_hub_intro.for": (
            "Цикл «for» повторяет команды исполнителя Робот известное число раз. "
            "Первое знакомство с циклом со счётчиком."
        ),
        "theme_hub_intro.forfun": (
            "Цикл «for» в сочетании с функциями помогает структурировать решения для "
            "исполнителя Робот. Задачи учат оформлять повторяющееся действие как "
            "функцию и вызывать её внутри цикла."
        ),
        "theme_hub_intro.w": (
            "Цикл «while» повторяет команды исполнителя Робот, пока условие истинно, "
            "что полезно, когда число шагов заранее неизвестно. Задачи посвящены "
            "движению до стены или до нужной клетки – основе навигации по полю с "
            "условиями."
        ),
        "theme_hub_intro.wfun": (
            "Цикл «while» вместе с функциями помогает структурировать решения "
            "исполнителя Робот, которые выполняются до изменения условия. Задачи "
            "учат выносить повторяющуюся проверку в функцию и вызывать её из цикла."
        ),
        "theme_hub_intro.if": (
            "Конструкция «if» позволяет исполнителю Робот действовать по-разному в "
            "зависимости от поля. Задачи знакомят с условным выполнением без цикла."
        ),
        "theme_hub_intro.wif": (
            "Цикл «while» с конструкцией «if» позволяет решать более интересные задачи "
            "с исполнителем Робот."
        ),
        "theme_hub_intro.ifelse": (
            "Пара «if» и «else» позволяет программе для исполнителя Робот выбрать "
            "одно из двух действий в зависимости от поля. Задачи учат ветвлению с "
            "альтернативой. Например, повернуть влево или вправо в зависимости от "
            "того, с какой стороны свободно."
        ),
        "theme_hub_intro.compound": (
            "Составные условия объединяют несколько проверок через «and» или «or». "
            "Задачи учат строить логические выражения с помощью команд анализа "
            "обстановки исполнителя Робот."
        ),
        "og_default_alt": "Окно Робота с задачей на клеточном поле.",
        "articles_nav": _RU_ARTICLES_LABEL,
        "articles_heading": _RU_ARTICLES_LABEL,
        "articles_page_title": _RU_ARTICLES_LABEL,
        "articles_intro": (
            "Подробные материалы об исполнителе Робот для учителей и учащихся."
        ),
        "articles_empty": "Пока нет опубликованных статей.",
        "editor_nav": "Редактор обстановок",
        "editor_intro": (
            "Пошаговая инструкция по созданию своих задач для исполнителя Робот "
            "с помощью встроенного редактора обстановок."
        ),
        "editor_step_1": (
            "Редактор обстановок находится в editor/editor.py. Скачайте архив модуля "
            "на странице {link} и из распакованного архива запустите:"
        ),
        "editor_step_2": "Создайте нужное количество обстановок для задачи.",
        "editor_step_3": "Сохраните файл обстановки в папку robot/tasks.",
        "editor_step_4": (
            "В программе на Python вызовите task() с именем файла без расширения .env."
        ),
        "editor_note_heading": "Замечание",
        "editor_note_p1": (
            "Редактор сохраняет условие задачи (todoText) одной строкой или редактирует "
            "одну локаль за раз, если в файле уже есть переводы. Чтобы изменить все "
            "переводы сразу, отредактируйте файл вручную."
        ),
        "editor_note_p2_intro": (
            "В редакторе можно задать ограничения на решение (кнопка ограничений на панели "
            "инструментов):"
        ),
        "editor_fig_editor": "Редактор обстановок.",
        "editor_example_task": "robot",
        "editor_online_heading": "Онлайн-редактор обстановок",
        "editor_online_text": (
            "Создавайте и редактируйте обстановки в браузере, без установки модуля."
        ),
        "editor_online_link": "Открыть онлайн-редактор",
        "editor_online_limit_size": (
            "Поддерживаются обстановки меньшего размера: до {rows} строк на {cols} колонок."
        ),
        "editor_online_limit_constraints": (
            "Не поддерживается задание ограничений на решение."
        ),
    },
}

ENV_FORMAT_DOC_BASE = {
    "en": (
        "https://github.com/step-in-dev/robot/blob/main/Docs/task-env-format.md"
    ),
    "ru": (
        "https://github.com/step-in-dev/robot/blob/main/Docs/task-env-format.ru.md"
    ),
}

_RU_IF_WHILE_ANCHOR = "iflimit-%D0%B8-whilelimit"
_RU_REQUIRED_BANNED_ANCHOR = "requiredkeywords-%D0%B8-bannedkeywords"

EDITOR_CONSTRAINT_DOC_ANCHORS: Dict[str, Dict[str, str]] = {
    "en": {
        "operatorsLimit": "operatorslimit",
        "customFunctionCallCount": "customfunctioncallcount",
        "ifLimit": "iflimit-and-whilelimit",
        "whileLimit": "iflimit-and-whilelimit",
        "requiredKeywords": "requiredkeywords-and-bannedkeywords",
        "bannedKeywords": "requiredkeywords-and-bannedkeywords",
    },
    "ru": {
        "operatorsLimit": "operatorslimit",
        "customFunctionCallCount": "customfunctioncallcount",
        "ifLimit": _RU_IF_WHILE_ANCHOR,
        "whileLimit": _RU_IF_WHILE_ANCHOR,
        "requiredKeywords": _RU_REQUIRED_BANNED_ANCHOR,
        "bannedKeywords": _RU_REQUIRED_BANNED_ANCHOR,
    },
}

COMMAND_GROUP_TITLES: Dict[str, Dict[str, str]] = {
    "en": {
        "task_field": "Choosing a task or creating a field",
        "movement": "Action commands",
        "cell_walls": "Environment analysis",
    },
    "ru": {
        "task_field": "Выбор задачи или создание поля",
        "movement": "Команды-действия",
        "cell_walls": "Анализ обстановки",
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
