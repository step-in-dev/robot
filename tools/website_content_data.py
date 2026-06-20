"""Static strings and URL constants for the Robot website generator."""

from __future__ import annotations

from typing import Dict, Tuple
from pathlib import Path

from robot.student_api import STUDENT_COMMAND_NAMES

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SITE_BASE = "https://robot.stepindev.com"
GITHUB_RELEASES_URL = "https://github.com/step-in-dev/robot/releases"
ONLINE_EDITOR_URL = {
    "en": "https://stepindev.com/en/py-robot",
    "ru": "https://stepindev.com/ru/py-robot",
}
ONLINE_EDITOR_MAX_ROWS = 8
ONLINE_EDITOR_MAX_COLS = 10
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
    (
        "movement",
        (
            "move_right",
            "move_left",
            "move_up",
            "move_down",
            "paint",
            "printn",
        ),
    ),
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
                "paint",
                "printn",
            )
        ),
    ),
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
            "An 'if' statement lets the Robot act differently depending on the field, "
            "such as painting only when a cell is not painted. These tasks introduce "
            "conditional execution without a loop."
        ),
        "theme_hub_intro.wif": (
            "A 'while' loop with an 'if' statement lets you solve more interesting "
            "tasks with the Robot."
        ),
        "theme_hub_intro.ifelse": (
            "An 'if' and 'else' pair lets the Robot choose between two actions based "
            "on the field. These tasks teach branching with an alternative. For "
            "example, turn left or right depending on which side is free."
        ),
        "theme_hub_intro.compound": (
            "Compound conditions combine several checks with 'and' or 'or'. These "
            "tasks teach building logical expressions with the Robot environment "
            "analysis commands."
        ),
        "og_default_alt": "Robot desktop window showing a grid programming task.",
        "articles_nav": "Articles",
        "articles_heading": "Articles",
        "articles_page_title": "Articles about the Robot simulator | Robot",
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
        "theme_hub_intro.intro": (
            "Первые шаги с исполнителем Робот: перемещение по полю, закраска клеток и "
            "достижение целевой клетки. Задачи знакомят с исполнителем Робот и учат "
            "составлять последовательности команд перед переходом к циклам и условиям."
        ),
        "theme_hub_intro.fun": (
            "Функции позволяют повторно использовать группу команд Робота вместо их "
            "повторения. Задачи учат определять собственную функцию и вызывать её, "
            "чтобы решения оставались короткими и понятными даже на больших полях."
        ),
        "theme_hub_intro.for": (
            "Цикл «for» повторяет команды Робота известное число раз. Первое знакомство "
            "с циклом со счётчиком."
        ),
        "theme_hub_intro.forfun": (
            "Цикл «for» в сочетании с функциями помогает структурировать решения для "
            "Робота. Задачи учат оформлять повторяющееся действие как функцию и "
            "вызывать её внутри цикла."
        ),
        "theme_hub_intro.w": (
            "Цикл «while» повторяет команды Робота, пока условие истинно, что полезно, "
            "когда число шагов заранее неизвестно. Задачи посвящены движению до стены "
            "или до нужной клетки – основе навигации по полю с условиями."
        ),
        "theme_hub_intro.wfun": (
            "Цикл «while» вместе с функциями помогает структурировать решения Робота, "
            "которые выполняются до изменения условия. Задачи учат выносить "
            "повторяющуюся проверку в функцию и вызывать её из цикла."
        ),
        "theme_hub_intro.if": (
            "Конструкция «if» позволяет Роботу действовать по-разному в зависимости от "
            "поля, например закрашивать только незакрашенную клетку. Задачи знакомят с "
            "условным выполнением без цикла."
        ),
        "theme_hub_intro.wif": (
            "Цикл «while» с конструкцией «if» позволяет решать более интересные задачи "
            "с исполнителем Робот."
        ),
        "theme_hub_intro.ifelse": (
            "Пара «if» и «else» позволяет Роботу выбрать одно из двух действий в "
            "зависимости от поля. Задачи учат ветвлению с альтернативой. Например, "
            "повернуть влево или вправо в зависимости от того, с какой стороны свободно."
        ),
        "theme_hub_intro.compound": (
            "Составные условия объединяют несколько проверок через «and» или «or». "
            "Задачи учат строить логические выражения с помощью команд анализа "
            "обстановки Робота."
        ),
        "og_default_alt": "Окно Робота с задачей на клеточном поле.",
        "articles_nav": "Статьи",
        "articles_heading": "Статьи",
        "articles_page_title": "Статьи об исполнителе Робот | Robot",
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

EDITOR_CONSTRAINT_FIELDS = (
    "operatorsLimit",
    "customFunctionCallCount",
    "ifLimit",
    "whileLimit",
    "requiredKeywords",
    "bannedKeywords",
)

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
