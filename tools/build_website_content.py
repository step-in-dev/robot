"""Generate SEO task catalog, command reference, and sitemap for the Robot website."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import argparse
import html
import json
import os
import re
import shutil
import struct
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# pylint: disable=wrong-import-position
from robot.command_help import COMMAND_HELP_SPECS, iter_command_help
from robot.gui_constraints import constraints_body_lines, task_has_any_constraints
from robot.i18n import DEFAULT_LANGUAGE, normalize_language, t
from robot.loader import ScriptConstraints, find_task_file, load_task_definition
from robot.task_catalog import (
    TaskCatalog,
    task_number_from_id,
    theme_from_task_id,
)

# pylint: enable=wrong-import-position

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
        (
            "paint",
            "is_free_left",
            "is_free_right",
            "is_free_up",
            "is_free_down",
            "is_wall_left",
            "is_wall_right",
            "is_wall_up",
            "is_wall_down",
            "is_cell_painted",
            "is_cell_not_painted",
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
        "tasks_nav": "Tasks",
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
        "constraints_heading": "Constraints",
        "example_heading": "Example in Python",
        "prev_task": "Previous task",
        "next_task": "Next task",
        "all_tasks_in_theme": "All tasks in this theme",
        "browse_catalog": "Browse the full task catalog",
        "theme_tasks_intro": "Tasks in this track, in lesson order.",
        "catalog_intro": "All bundled Robot tasks grouped by topic. Each page shows the task condition, field layouts, and limits.",
        "commands_intro": "Student-facing Python API for the Robot simulator. Use from robot import * or import only the names you need.",
        "tasks_in_theme": "{count} tasks",
        "task_count_total": "{count} tasks in total",
        "og_default_alt": "Robot desktop window showing a grid programming task.",
    },
    "ru": {
        "site_name": "Робот",
        "home": "Главная",
        "task_catalog": "Каталог задач",
        "command_reference": "Справочник команд",
        "tasks_nav": "Задачи",
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
        "constraints_heading": "Ограничения",
        "example_heading": "Пример на Python",
        "prev_task": "Предыдущая задача",
        "next_task": "Следующая задача",
        "all_tasks_in_theme": "Все задачи темы",
        "browse_catalog": "Открыть полный каталог задач",
        "theme_tasks_intro": "Задачи темы в порядке, как на уроке.",
        "catalog_intro": "Все встроенные задачи Робота по темам. На странице задачи – условие, поля обстановок и ограничения.",
        "commands_intro": "Команды Python для учащихся в исполнителе «Робот». Можно подключить всё через from robot import * или импортировать отдельные имена.",
        "tasks_in_theme": "Задач: {count}",
        "task_count_total": "Всего задач: {count}",
        "og_default_alt": "Окно Робота с задачей на клеточном поле.",
    },
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

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_dashes(text: str) -> str:
    """Use en dash (–) on the site; normalize em dash and horizontal bar from sources."""
    return text.replace("\u2014", "\u2013").replace("\u2015", "\u2013")


def _ui(lang: str, key: str, **kwargs: object) -> str:
    text = UI_STRINGS[lang][key]
    return text.format(**kwargs) if kwargs else text


def resolve_todo_text_for_language(raw: Any, language: str) -> str:
    """Like :func:`robot.loader.resolve_todo_text` but for a fixed site language."""
    if isinstance(raw, str):
        return raw
    if not isinstance(raw, dict):
        return ""
    by_lang: Dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        norm = normalize_language(key)
        if norm is not None:
            by_lang[norm] = value
    if not by_lang:
        return ""
    if language in by_lang:
        return by_lang[language]
    if DEFAULT_LANGUAGE in by_lang:
        return by_lang[DEFAULT_LANGUAGE]
    return next(iter(by_lang.values()), "")


def load_raw_todo_text(task_id: str) -> Any:
    """Read ``todoText`` from the task JSON without resolving UI language."""
    task_path = find_task_file(task_id)
    with task_path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    return data.get("todoText", "")


def escape(text: str) -> str:
    return html.escape(normalize_dashes(text), quote=True)


def normalize_meta_description(text: str, limit: int = 155) -> str:
    compact = _WHITESPACE_RE.sub(" ", normalize_dashes(text.strip()))
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def rel_prefix(depth: int) -> str:
    if depth <= 0:
        return ""
    return "../" * depth


def page_filename(lang: str, base: str = "index") -> str:
    if lang == "ru":
        return f"{base}_ru.html"
    return f"{base}.html"


def task_page_filename(task_id: str, lang: str) -> str:
    return page_filename(lang, task_id)


def theme_slug(theme_prefix: str) -> str:
    slug = THEME_URL_SLUG.get(theme_prefix)
    if slug is None:
        raise KeyError(f"No URL slug configured for theme {theme_prefix!r}")
    return slug


def theme_hub_relpath(theme_prefix: str, lang: str) -> str:
    return f"tasks/{theme_slug(theme_prefix)}/{page_filename(lang)}"


def catalog_relpath(lang: str) -> str:
    return f"tasks/{page_filename(lang)}"


def commands_relpath(lang: str) -> str:
    return page_filename(lang, "commands")


def task_page_relpath(task_id: str, lang: str) -> str:
    return f"tasks/{task_page_filename(task_id, lang)}"


def absolute_url(relative_path: str) -> str:
    if relative_path in ("index.html", "/"):
        return f"{SITE_BASE}/"
    return f"{SITE_BASE}/{relative_path.lstrip('/')}"


def png_dimensions(path: Path) -> Optional[Tuple[int, int]]:
    try:
        with path.open("rb") as stream:
            header = stream.read(24)
        if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        width, height = struct.unpack(">II", header[16:24])
        return width, height
    except OSError:
        return None


def task_screenshot_path(task_id: str, env_index: int) -> Path:
    """Return path to a field PNG, with legacy ``_en`` fallback during migration."""
    primary = TASKS_IMG_DIR / f"{task_id}_env{env_index}.png"
    if primary.is_file():
        return primary
    legacy = TASKS_IMG_DIR / f"{task_id}_env{env_index}_en.png"
    if legacy.is_file():
        return legacy
    return primary


def theme_title(theme_prefix: str) -> str:
    return t(f"help.task_group.{theme_prefix}")


@dataclass(frozen=True)
class PageLayout:
    lang: str
    depth: int
    page_kind: str
    title: str
    description: str
    canonical_path: str
    alternate_en: str
    alternate_ru: str
    og_image_path: Optional[str] = None
    og_image_alt: Optional[str] = None
    json_ld: Optional[dict] = None

    @property
    def asset_prefix(self) -> str:
        return rel_prefix(self.depth)

    def href(self, relative_to_site_root: str) -> str:
        return f"{self.asset_prefix}{relative_to_site_root}"

    def site_url(self, relative_to_site_root: str) -> str:
        return absolute_url(relative_to_site_root)


def _set_language(lang: str) -> Optional[str]:
    previous = os.environ.get("ROBOT_LANGUAGE")
    os.environ["ROBOT_LANGUAGE"] = lang
    return previous


def _restore_language(previous: Optional[str]) -> None:
    if previous is None:
        os.environ.pop("ROBOT_LANGUAGE", None)
    else:
        os.environ["ROBOT_LANGUAGE"] = previous


def localized_constraints(constraints: ScriptConstraints, lang: str) -> List[str]:
    previous = _set_language(lang)
    try:
        return constraints_body_lines(constraints)
    finally:
        _restore_language(previous)


def localized_command_help(lang: str) -> List[Tuple[str, str]]:
    previous = _set_language(lang)
    try:
        return iter_command_help()
    finally:
        _restore_language(previous)


def render_head(layout: PageLayout) -> str:
    og_image = layout.og_image_path or "img/hero/intro19_en.png"
    if layout.lang == "ru" and og_image.endswith("_en.png"):
        og_image = og_image.replace("_en.png", "_ru.png")
    og_image_url = layout.site_url(og_image)
    og_alt = escape(layout.og_image_alt or _ui(layout.lang, "og_default_alt"))
    dims = png_dimensions(WEBSITE_DIR / og_image)
    dim_tags = ""
    if dims:
        width, height = dims
        dim_tags = (
            f'  <meta property="og:image:width" content="{width}">\n'
            f'  <meta property="og:image:height" content="{height}">\n'
        )
    json_ld_block = ""
    if layout.json_ld is not None:
        json_ld_block = (
            f'  <script type="application/ld+json">\n'
            f"{json.dumps(layout.json_ld, ensure_ascii=False, indent=2)}\n"
            f"  </script>\n"
        )
    locale = "ru_RU" if layout.lang == "ru" else "en_US"
    alt_locale = "en_US" if layout.lang == "ru" else "ru_RU"
    html_lang = "ru" if layout.lang == "ru" else "en"
    return f"""<!DOCTYPE html>
<html lang="{html_lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(layout.title)}</title>
  <meta name="description" content="{escape(layout.description)}">
  <link rel="canonical" href="{escape(layout.site_url(layout.canonical_path))}">
  <link rel="alternate" hreflang="en" href="{escape(absolute_url(layout.alternate_en))}">
  <link rel="alternate" hreflang="ru" href="{escape(absolute_url(layout.alternate_ru))}">
  <link rel="alternate" hreflang="x-default" href="{escape(absolute_url(layout.alternate_en))}">
  <meta property="og:title" content="{escape(layout.title)}">
  <meta property="og:description" content="{escape(layout.description)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{escape(layout.site_url(layout.canonical_path))}">
  <meta property="og:site_name" content="Robot">
  <meta property="og:image" content="{escape(og_image_url)}">
  <meta property="og:image:alt" content="{og_alt}">
{dim_tags}  <meta property="og:locale" content="{locale}">
  <meta property="og:locale:alternate" content="{alt_locale}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(layout.title)}">
  <meta name="twitter:description" content="{escape(layout.description)}">
  <meta name="twitter:image" content="{escape(og_image_url)}">
{json_ld_block}  <link rel="icon" href="{layout.href("favicon.svg")}" type="image/svg+xml">
  <link rel="stylesheet" href="{layout.href("styles.css")}">
</head>
"""


def render_header(layout: PageLayout) -> str:
    home_page = "index_ru.html" if layout.lang == "ru" else "index.html"
    en_link = layout.href(layout.alternate_en)
    ru_link = layout.href(layout.alternate_ru)
    if layout.lang == "en":
        lang_en_class = ' class="is-active" aria-current="page"'
        lang_ru_class = ""
    else:
        lang_en_class = ""
        lang_ru_class = ' class="is-active" aria-current="page"'
    brand_current = ""
    catalog = layout.href(catalog_relpath(layout.lang))
    commands = layout.href(commands_relpath(layout.lang))
    return f"""  <a class="skip-link" href="#main">{_ui(layout.lang, "skip")}</a>
  <header class="site-header">
    <div class="site-header__inner">
      <a class="brand" href="{layout.href(home_page)}"{brand_current}>
        <span class="brand__mark" aria-hidden="true"></span>
        <span class="brand__text">{escape(_ui(layout.lang, "site_name"))}</span>
      </a>
      <button type="button" class="nav-toggle" id="nav-toggle" aria-expanded="false" aria-controls="site-nav" aria-label="{escape(_ui(layout.lang, "open_menu"))}">
        <span class="nav-toggle__bar"></span>
        <span class="nav-toggle__bar"></span>
        <span class="nav-toggle__bar"></span>
      </button>
      <nav class="site-nav" id="site-nav" aria-label="{escape(_ui(layout.lang, "primary_nav"))}">
        <ul class="site-nav__list">
          <li><a href="{catalog}">{escape(_ui(layout.lang, "tasks_nav"))}</a></li>
          <li><a href="{commands}">{escape(_ui(layout.lang, "command_reference"))}</a></li>
          <li><a href="https://github.com/step-in-dev/robot" rel="noopener noreferrer" target="_blank">{escape(_ui(layout.lang, "github"))}</a></li>
        </ul>
        <p class="site-nav__lang">
          <a href="{en_link}" hreflang="en"{lang_en_class}>{escape(_ui(layout.lang, "english"))}</a>
          <span class="site-nav__lang-sep" aria-hidden="true">·</span>
          <a href="{ru_link}" hreflang="ru"{lang_ru_class}>{escape(_ui(layout.lang, "russian"))}</a>
        </p>
      </nav>
    </div>
  </header>
"""


def render_footer(layout: PageLayout) -> str:
    home_page = "index_ru.html" if layout.lang == "ru" else "index.html"
    catalog = layout.href(catalog_relpath(layout.lang))
    commands = layout.href(commands_relpath(layout.lang))
    return f"""  <footer class="site-footer">
    <div class="site-footer__inner">
      <p class="site-footer__brand"><span class="brand__mark brand__mark--small" aria-hidden="true"></span> {escape(_ui(layout.lang, "footer_tagline"))}</p>
      <ul class="site-footer__links">
        <li><a href="{layout.href(home_page)}">{escape(_ui(layout.lang, "home"))}</a></li>
        <li><a href="{catalog}">{escape(_ui(layout.lang, "task_catalog"))}</a></li>
        <li><a href="{commands}">{escape(_ui(layout.lang, "command_reference"))}</a></li>
        <li><a href="{layout.href(layout.alternate_en)}" hreflang="en">English</a></li>
        <li><a href="{layout.href(layout.alternate_ru)}" hreflang="ru">Русский</a></li>
        <li><a href="https://github.com/step-in-dev/robot" rel="noopener noreferrer" target="_blank">GitHub</a></li>
        <li><a href="https://github.com/step-in-dev/robot/releases" rel="noopener noreferrer" target="_blank">{escape(_ui(layout.lang, "releases"))}</a></li>
      </ul>
    </div>
  </footer>

  <script src="{layout.href("script.js")}" defer></script>
"""


def render_breadcrumbs(layout: PageLayout, items: Sequence[Tuple[str, str]]) -> str:
    parts = ['<nav class="breadcrumbs" aria-label="Breadcrumb">', "<ol>"]
    for index, (label, site_path) in enumerate(items):
        if index == len(items) - 1:
            parts.append(f"<li aria-current=\"page\">{escape(label)}</li>")
        else:
            href = layout.href(site_path)
            parts.append(f'<li><a href="{escape(href)}">{escape(label)}</a></li>')
    parts.append("</ol></nav>")
    return "\n".join(parts)


def breadcrumb_json_ld(items: Sequence[Tuple[str, str]]) -> dict:
    elements = []
    for position, (name, site_path) in enumerate(items, start=1):
        elements.append(
            {
                "@type": "ListItem",
                "position": position,
                "name": name,
                "item": absolute_url(site_path),
            }
        )
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": elements,
    }


def wrap_page(layout: PageLayout, main_html: str) -> str:
    return (
        render_head(layout)
        + "<body>\n"
        + render_header(layout)
        + f'\n  <main id="main" class="content-page">\n{main_html}\n  </main>\n\n'
        + render_footer(layout)
        + "</body>\n</html>\n"
    )


def write_page(path: Path, html_text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_text, encoding="utf-8")


def first_available_task_image(task_id: str, env_count: int) -> Optional[str]:
    for env_index in range(env_count):
        shot = task_screenshot_path(task_id, env_index)
        if shot.is_file():
            return f"img/tasks/{shot.name}"
    return None


def render_environment_figures(
    layout: PageLayout,
    *,
    task_id: str,
    env_count: int,
) -> str:
    blocks: List[str] = []
    for env_index in range(env_count):
        shot = task_screenshot_path(task_id, env_index)
        if not shot.is_file():
            continue
        rel = f"img/tasks/{shot.name}"
        alt = escape(
            f"{task_id} – {_ui(layout.lang, 'environment_n', n=env_index + 1)}"
        )
        dim_attr = ""
        dims = png_dimensions(shot)
        if dims:
            width, height = dims
            dim_attr = f' width="{width}" height="{height}"'
        blocks.append(
            f"""        <figure class="env-figure">
          <img src="{layout.href(rel)}" alt="{alt}"{dim_attr} loading="lazy">
          <figcaption>{escape(_ui(layout.lang, "environment_n", n=env_index + 1))}</figcaption>
        </figure>"""
        )
    if not blocks:
        return ""
    heading = escape(_ui(layout.lang, "environments_heading"))
    return f"""      <section class="task-envs" aria-labelledby="envs-heading">
        <h2 id="envs-heading">{heading}</h2>
        <div class="env-figure-grid">
{chr(10).join(blocks)}
        </div>
      </section>
"""


def build_task_page(
    catalog: TaskCatalog,
    task_id: str,
    lang: str,
) -> str:
    theme = catalog.current_theme_for_task(task_id)
    if theme is None:
        raise ValueError(f"Task {task_id!r} not in catalog")
    task_def = load_task_definition(task_id)
    todo = resolve_todo_text_for_language(load_raw_todo_text(task_id), lang)
    number = task_number_from_id(task_id)
    theme_label = theme_title(theme)
    title = f"{task_id} – {theme_label} | Robot"
    description = normalize_meta_description(todo or f"Robot task {task_id}.")
    canonical = task_page_relpath(task_id, lang)
    og_image = first_available_task_image(task_id, len(task_def.envs))

    crumbs = [
        (_ui(lang, "home"), "index_ru.html" if lang == "ru" else "index.html"),
        (_ui(lang, "task_catalog"), catalog_relpath(lang)),
        (theme_label, theme_hub_relpath(theme, lang)),
        (task_id, canonical),
    ]

    ids = catalog.task_ids_for(theme)
    idx = ids.index(task_id)
    nav_bits: List[str] = []
    if idx > 0:
        prev_id = ids[idx - 1]
        nav_bits.append(
            f'<a class="task-nav__link" href="{task_page_filename(prev_id, lang)}">'
            f"← {escape(_ui(lang, 'prev_task'))}: <code>{escape(prev_id)}</code></a>"
        )
    if idx + 1 < len(ids):
        next_id = ids[idx + 1]
        nav_bits.append(
            f'<a class="task-nav__link" href="{task_page_filename(next_id, lang)}">'
            f"{escape(_ui(lang, 'next_task'))}: <code>{escape(next_id)}</code> →</a>"
        )
    task_nav = ""
    if nav_bits:
        task_nav = f'<nav class="task-nav" aria-label="Task navigation">{" ".join(nav_bits)}</nav>'

    constraints_html = ""
    if task_has_any_constraints(task_def.script_constraints):
        lines = localized_constraints(task_def.script_constraints, lang)
        items = "\n".join(f"          <li>{escape(line)}</li>" for line in lines)
        constraints_html = f"""      <section class="task-constraints" aria-labelledby="constraints-heading">
        <h2 id="constraints-heading">{escape(_ui(lang, "constraints_heading"))}</h2>
        <ul>
{items}
        </ul>
      </section>
"""

    env_html = render_environment_figures(
        PageLayout(
            lang=lang,
            depth=1,
            page_kind="task",
            title=title,
            description=description,
            canonical_path=canonical,
            alternate_en=task_page_relpath(task_id, "en"),
            alternate_ru=task_page_relpath(task_id, "ru"),
        ),
        task_id=task_id,
        env_count=len(task_def.envs),
    )

    todo_html = escape(todo).replace("\n", "<br>\n        ")
    h1 = f"<code>{escape(task_id)}</code> – {escape(theme_label)}"
    if number is not None:
        h1 = f'{h1} <span class="task-number">#{number}</span>'

    layout = PageLayout(
        lang=lang,
        depth=1,
        page_kind="task",
        title=title,
        description=description,
        canonical_path=canonical,
        alternate_en=task_page_relpath(task_id, "en"),
        alternate_ru=task_page_relpath(task_id, "ru"),
        og_image_path=og_image,
        json_ld={
            "@context": "https://schema.org",
            "@graph": [
                breadcrumb_json_ld(crumbs),
                {
                    "@type": "LearningResource",
                    "name": task_id,
                    "description": description,
                    "inLanguage": lang,
                    "learningResourceType": "problem",
                    "url": absolute_url(canonical),
                },
            ],
        },
    )
    crumb_html = render_breadcrumbs(layout, crumbs)

    main = f"""    <article class="task-page">
      {crumb_html}
      <header class="content-header">
        <h1>{h1}</h1>
      </header>
      <div class="task-condition">{todo_html}</div>
{env_html}{constraints_html}      <section class="code-showcase" aria-labelledby="example-heading">
        <h2 id="example-heading">{escape(_ui(lang, "example_heading"))}</h2>
        <pre class="code-block"><code>from robot import *

task("{escape(task_id)}")</code></pre>
      </section>
      {task_nav}
      <p class="content-outro"><a href="{layout.href(theme_hub_relpath(theme, lang))}">{escape(_ui(lang, "all_tasks_in_theme"))}</a> · <a href="{layout.href(catalog_relpath(lang))}">{escape(_ui(lang, "browse_catalog"))}</a></p>
    </article>
"""
    return wrap_page(layout, main)


def build_theme_hub(catalog: TaskCatalog, theme_prefix: str, lang: str) -> str:
    task_ids = catalog.task_ids_for(theme_prefix)
    theme_label = theme_title(theme_prefix)
    slug = theme_slug(theme_prefix)
    canonical = f"tasks/{slug}/{page_filename(lang)}"
    title = f"{theme_label} – Robot tasks"
    description = normalize_meta_description(
        f"{theme_label}. {_ui(lang, 'theme_tasks_intro')}"
    )
    crumbs = [
        (_ui(lang, "home"), "index_ru.html" if lang == "ru" else "index.html"),
        (_ui(lang, "task_catalog"), catalog_relpath(lang)),
        (theme_label, canonical),
    ]

    item_list = {
        "@type": "ItemList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "url": absolute_url(task_page_relpath(task_id, lang)),
                "name": task_id,
            }
            for index, task_id in enumerate(task_ids, start=1)
        ],
    }
    layout = PageLayout(
        lang=lang,
        depth=2,
        page_kind="theme",
        title=title,
        description=description,
        canonical_path=canonical,
        alternate_en=f"tasks/{slug}/{page_filename('en')}",
        alternate_ru=f"tasks/{slug}/{page_filename('ru')}",
        json_ld={
            "@context": "https://schema.org",
            "@graph": [
                breadcrumb_json_ld(crumbs),
                {
                    "@type": "CollectionPage",
                    "name": theme_label,
                    "description": description,
                    "inLanguage": lang,
                    "url": absolute_url(canonical),
                    "mainEntity": item_list,
                },
            ],
        },
    )
    crumb_html = render_breadcrumbs(layout, crumbs)

    items: List[str] = []
    for task_id in task_ids:
        todo = resolve_todo_text_for_language(load_raw_todo_text(task_id), lang)
        snippet = normalize_meta_description(todo, limit=120)
        task_href = layout.href(task_page_relpath(task_id, lang))
        items.append(
            f"""          <li class="task-list__item">
            <h2 class="task-list__title"><a href="{escape(task_href)}"><code>{escape(task_id)}</code></a></h2>
            <p class="task-list__snippet">{escape(snippet)}</p>
          </li>"""
        )

    main = f"""    <div class="hub-page">
      {crumb_html}
      <header class="content-header">
        <h1>{escape(theme_label)}</h1>
        <p class="section__intro">{escape(_ui(lang, "theme_tasks_intro"))} {escape(_ui(lang, "tasks_in_theme", count=len(task_ids)))}</p>
      </header>
      <ul class="task-list">
{chr(10).join(items)}
      </ul>
      <p class="content-outro"><a href="{layout.href(catalog_relpath(lang))}">← {escape(_ui(lang, "task_catalog"))}</a></p>
    </div>
"""
    return wrap_page(layout, main)


def build_catalog(catalog: TaskCatalog, lang: str) -> str:
    canonical = catalog_relpath(lang)
    title = f"{_ui(lang, 'task_catalog')} | Robot"
    description = normalize_meta_description(_ui(lang, "catalog_intro"))
    crumbs = [
        (_ui(lang, "home"), "index_ru.html" if lang == "ru" else "index.html"),
        (_ui(lang, "task_catalog"), canonical),
    ]

    layout = PageLayout(
        lang=lang,
        depth=1,
        page_kind="catalog",
        title=title,
        description=description,
        canonical_path=canonical,
        alternate_en=catalog_relpath("en"),
        alternate_ru=catalog_relpath("ru"),
        json_ld={
            "@context": "https://schema.org",
            "@graph": [
                breadcrumb_json_ld(crumbs),
                {
                    "@type": "CollectionPage",
                    "name": _ui(lang, "task_catalog"),
                    "description": description,
                    "inLanguage": lang,
                    "url": absolute_url(canonical),
                },
            ],
        },
    )
    crumb_html = render_breadcrumbs(layout, crumbs)

    total = sum(len(catalog.task_ids_for(theme)) for theme in catalog.themes)
    theme_blocks: List[str] = []
    for theme_prefix in catalog.themes:
        task_ids = catalog.task_ids_for(theme_prefix)
        if not task_ids:
            continue
        theme_label = theme_title(theme_prefix)
        slug = theme_slug(theme_prefix)
        range_text = f"<code>{escape(task_ids[0])}</code> … <code>{escape(task_ids[-1])}</code>"
        theme_href = layout.href(f"tasks/{slug}/{page_filename(lang)}")
        theme_blocks.append(
            f"""          <li class="theme-card">
            <h2><a href="{escape(theme_href)}">{escape(theme_label)}</a></h2>
            <p>{range_text} · {escape(_ui(lang, "tasks_in_theme", count=len(task_ids)))}</p>
          </li>"""
        )

    main = f"""    <div class="hub-page">
      {crumb_html}
      <header class="content-header">
        <h1>{escape(_ui(lang, "task_catalog"))}</h1>
        <p class="section__intro">{escape(_ui(lang, "catalog_intro"))} {escape(_ui(lang, "task_count_total", count=total))}</p>
        <p><a href="{layout.href(commands_relpath(lang))}">{escape(_ui(lang, "command_reference"))}</a></p>
      </header>
      <ul class="theme-card-list">
{chr(10).join(theme_blocks)}
      </ul>
    </div>
"""
    return wrap_page(layout, main)


def build_commands_page(lang: str) -> str:
    canonical = commands_relpath(lang)
    title = f"{_ui(lang, 'command_reference')} | Robot"
    description = normalize_meta_description(_ui(lang, "commands_intro"))
    crumbs = [
        (_ui(lang, "home"), "index_ru.html" if lang == "ru" else "index.html"),
        (_ui(lang, "command_reference"), canonical),
    ]

    help_by_key = {key: "" for key, _ in COMMAND_HELP_SPECS}
    for signature, desc in localized_command_help(lang):
        for key, _spec_sig in COMMAND_HELP_SPECS:
            if signature.startswith(key):
                help_by_key[key] = desc
                break

    sig_map = {key: signature for key, signature in COMMAND_HELP_SPECS}
    groups_html: List[str] = []
    for group_id, keys in COMMAND_GROUPS:
        entries = []
        for key in keys:
            entries.append(
                f"              <dt><code>{escape(sig_map[key])}</code></dt>"
                f"<dd>{escape(help_by_key[key])}</dd>"
            )
        groups_html.append(
            f"""          <article class="command-group">
            <h2>{escape(COMMAND_GROUP_TITLES[lang][group_id])}</h2>
            <dl>
{chr(10).join(entries)}
            </dl>
          </article>"""
        )

    layout = PageLayout(
        lang=lang,
        depth=0,
        page_kind="commands",
        title=title,
        description=description,
        canonical_path=canonical,
        alternate_en=commands_relpath("en"),
        alternate_ru=commands_relpath("ru"),
        json_ld={
            "@context": "https://schema.org",
            "@graph": [
                breadcrumb_json_ld(crumbs),
                {
                    "@type": "TechArticle",
                    "name": _ui(lang, "command_reference"),
                    "description": description,
                    "inLanguage": lang,
                    "url": absolute_url(canonical),
                },
            ],
        },
    )
    crumb_html = render_breadcrumbs(layout, crumbs)

    main = f"""    <div class="hub-page commands-page">
      {crumb_html}
      <header class="content-header">
        <h1>{escape(_ui(lang, "command_reference"))}</h1>
        <p class="section__intro">{escape(_ui(lang, "commands_intro"))}</p>
        <p><a href="{layout.href(catalog_relpath(lang))}">{escape(_ui(lang, "task_catalog"))}</a></p>
      </header>
      <div class="command-grid">
{chr(10).join(groups_html)}
      </div>
    </div>
"""
    return wrap_page(layout, main)


def collect_sitemap_urls(catalog: TaskCatalog, lastmod: str) -> List[Tuple[str, str, str]]:
    """Return (en_path, ru_path, lastmod) tuples for alternate URL groups."""
    groups: List[Tuple[str, str, str]] = [
        ("index.html", "index_ru.html", lastmod),
        (commands_relpath("en"), commands_relpath("ru"), lastmod),
        (catalog_relpath("en"), catalog_relpath("ru"), lastmod),
    ]
    for theme_prefix in catalog.themes:
        slug = theme_slug(theme_prefix)
        groups.append(
            (
                f"tasks/{slug}/index.html",
                f"tasks/{slug}/index_ru.html",
                lastmod,
            )
        )
    for theme_prefix in catalog.themes:
        for task_id in catalog.task_ids_for(theme_prefix):
            groups.append(
                (
                    task_page_relpath(task_id, "en"),
                    task_page_relpath(task_id, "ru"),
                    lastmod,
                )
            )
    return groups


def _sitemap_loc(path: str) -> str:
    if path == "index.html":
        return f"{SITE_BASE}/"
    return absolute_url(path)


def write_sitemap(catalog: TaskCatalog, lastmod: str) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for en_path, ru_path, mod in collect_sitemap_urls(catalog, lastmod):
        en_href = _sitemap_loc(en_path)
        ru_href = _sitemap_loc(ru_path)
        for loc_path in (en_path, ru_path):
            lines.extend(
                [
                    "  <url>",
                    f"    <loc>{_sitemap_loc(loc_path)}</loc>",
                    f"    <lastmod>{mod}</lastmod>",
                    f'    <xhtml:link rel="alternate" hreflang="en" href="{en_href}"/>',
                    f'    <xhtml:link rel="alternate" hreflang="ru" href="{ru_href}"/>',
                    f'    <xhtml:link rel="alternate" hreflang="x-default" href="{en_href}"/>',
                    "  </url>",
                ]
            )
    lines.append("</urlset>")
    (WEBSITE_DIR / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def tasks_lastmod(catalog: TaskCatalog) -> str:
    newest = 0.0
    for theme_prefix in catalog.themes:
        for task_id in catalog.task_ids_for(theme_prefix):
            path = find_task_file(task_id)
            try:
                newest = max(newest, path.stat().st_mtime)
            except OSError:
                continue
    if newest <= 0:
        return date.today().isoformat()
    return date.fromtimestamp(newest).isoformat()


def clean_generated_tasks_dir() -> None:
    tasks_dir = WEBSITE_DIR / "tasks"
    if tasks_dir.is_dir():
        shutil.rmtree(tasks_dir)
    tasks_dir.mkdir(parents=True)


def generate_all() -> TaskCatalog:
    catalog = TaskCatalog.discover()
    clean_generated_tasks_dir()
    TASKS_IMG_DIR.mkdir(parents=True, exist_ok=True)

    for lang in SUPPORTED_SITE_LANGS:
        write_page(WEBSITE_DIR / commands_relpath(lang), build_commands_page(lang))
        write_page(WEBSITE_DIR / catalog_relpath(lang), build_catalog(catalog, lang))

    for theme_prefix in catalog.themes:
        slug = theme_slug(theme_prefix)
        for lang in SUPPORTED_SITE_LANGS:
            out = WEBSITE_DIR / "tasks" / slug / page_filename(lang)
            write_page(out, build_theme_hub(catalog, theme_prefix, lang))

    for theme_prefix in catalog.themes:
        for task_id in catalog.task_ids_for(theme_prefix):
            for lang in SUPPORTED_SITE_LANGS:
                out = WEBSITE_DIR / "tasks" / task_page_filename(task_id, lang)
                write_page(out, build_task_page(catalog, task_id, lang))

    lastmod = tasks_lastmod(catalog)
    write_sitemap(catalog, lastmod)
    return catalog


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    catalog = generate_all()
    task_count = sum(len(catalog.task_ids_for(t)) for t in catalog.themes)
    print(
        f"Generated {task_count} task pages × {len(SUPPORTED_SITE_LANGS)} languages, "
        f"{len(catalog.themes)} theme hubs, command reference, and sitemap."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
