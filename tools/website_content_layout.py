"""HTML layout helpers and page shell rendering for the Robot website generator."""

from __future__ import annotations

from typing import Any, List, Optional, Sequence, Tuple
import html
import json
import os
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

from robot.command_help import iter_command_help
from robot.gui_constraints import constraints_body_lines
from robot.i18n import DEFAULT_LANGUAGE, t
from robot.loader import ScriptConstraints, find_task_file
from robot.task_todo import normalized_todo_text_map

from tools.website_content_data import (
    SITE_BASE,
    TASKS_IMG_DIR,
    THEME_URL_SLUG,
    UI_STRINGS,
    WEBSITE_DIR,
)

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_dashes(text: str) -> str:
    """Use en dash (–) on the site; normalize em dash and horizontal bar from sources."""
    return text.replace("\u2014", "\u2013").replace("\u2015", "\u2013")


def _ui(lang: str, key: str, **kwargs: object) -> str:
    """Return a localized UI string for ``lang``, formatting with ``kwargs`` when given."""
    text = UI_STRINGS[lang][key]
    return text.format(**kwargs) if kwargs else text


def resolve_todo_text_for_language(raw: Any, language: str) -> str:
    """Like :func:`robot.task_todo.resolve_todo_text` but for a fixed site language."""
    if isinstance(raw, str):
        return raw
    if not isinstance(raw, dict):
        return ""
    by_lang = normalized_todo_text_map(raw)
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
    """Escape ``text`` for HTML and normalize dash characters."""
    return html.escape(normalize_dashes(text), quote=True)


def normalize_meta_description(text: str, limit: int = 155) -> str:
    """Collapse whitespace and truncate ``text`` for a meta description tag."""
    compact = _WHITESPACE_RE.sub(" ", normalize_dashes(text.strip()))
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def rel_prefix(depth: int) -> str:
    """Return a ``../`` prefix for assets at ``depth`` below the site root."""
    if depth <= 0:
        return ""
    return "../" * depth


def page_filename(lang: str, base: str = "index") -> str:
    """Return ``index.html`` or ``index_ru.html`` (or a custom ``base``) for ``lang``."""
    if lang == "ru":
        return f"{base}_ru.html"
    return f"{base}.html"


def task_page_filename(task_id: str, lang: str) -> str:
    """Return the HTML filename for a task page in ``lang``."""
    return page_filename(lang, task_id)


def theme_slug(theme_prefix: str) -> str:
    """Map an internal theme prefix to its public URL slug."""
    slug = THEME_URL_SLUG.get(theme_prefix)
    if slug is None:
        raise KeyError(f"No URL slug configured for theme {theme_prefix!r}")
    return slug


def theme_hub_relpath(theme_prefix: str, lang: str) -> str:
    """Return the site-relative path to a theme hub page."""
    return f"tasks/{theme_slug(theme_prefix)}/{page_filename(lang)}"


def catalog_relpath(lang: str) -> str:
    """Return the site-relative path to the task catalog index."""
    return f"tasks/{page_filename(lang)}"


def commands_relpath(lang: str) -> str:
    """Return the site-relative path to the command reference page."""
    return page_filename(lang, "commands")


def editor_relpath(lang: str) -> str:
    """Return the site-relative path to the environment editor guide."""
    return page_filename(lang, "editor")


def articles_index_relpath(lang: str) -> str:
    """Return the site-relative path to the articles index."""
    return f"articles/{page_filename(lang)}"


def home_relpath(lang: str) -> str:
    """Return the site-relative path to the home page for ``lang``."""
    return "index_ru.html" if lang == "ru" else "index.html"


def get_started_href(layout: PageLayout) -> str:
    """Return the href for the Get started nav link on ``layout``."""
    if layout.page_kind == "home":
        return "#get-started"
    return layout.href(f"{home_relpath(layout.lang)}#get-started")


def task_page_relpath(task_id: str, lang: str) -> str:
    """Return the site-relative path to a task detail page."""
    return f"tasks/{task_page_filename(task_id, lang)}"


def absolute_url(relative_path: str) -> str:
    """Turn a site-relative path into an absolute ``SITE_BASE`` URL."""
    if relative_path in ("index.html", "/"):
        return f"{SITE_BASE}/"
    return f"{SITE_BASE}/{relative_path.lstrip('/')}"


def webp_dimensions(path: Path) -> Optional[Tuple[int, int]]:
    """Read width and height from a WebP header, or return ``None`` on failure."""
    try:
        with path.open("rb") as stream:
            header = stream.read(30)
        if len(header) < 25 or header[0:4] != b"RIFF" or header[8:12] != b"WEBP":
            return None
        if header[12:16] == b"VP8L":
            bits = int.from_bytes(header[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if header[12:16] == b"VP8 " and len(header) >= 30:
            bits = int.from_bytes(header[26:29], "little")
            return bits & 0x3FFF, (bits >> 14) & 0x3FFF
        return None
    except OSError:
        return None


def png_dimensions(path: Path) -> Optional[Tuple[int, int]]:
    """Read width and height from a PNG header, or return ``None`` on failure."""
    try:
        with path.open("rb") as stream:
            header = stream.read(24)
        if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        width, height = struct.unpack(">II", header[16:24])
        return width, height
    except OSError:
        return None


def image_dimensions(path: Path) -> Optional[Tuple[int, int]]:
    """Read width and height from a PNG or WebP file."""
    suffix = path.suffix.lower()
    if suffix == ".webp":
        return webp_dimensions(path)
    if suffix == ".png":
        return png_dimensions(path)
    return webp_dimensions(path) or png_dimensions(path)


def task_screenshot_path(task_id: str, env_index: int) -> Path:
    """Return path to a field screenshot, with legacy PNG fallbacks during migration."""
    primary = TASKS_IMG_DIR / f"{task_id}_env{env_index}.webp"
    if primary.is_file():
        return primary
    legacy_png = TASKS_IMG_DIR / f"{task_id}_env{env_index}.png"
    if legacy_png.is_file():
        return legacy_png
    legacy_en = TASKS_IMG_DIR / f"{task_id}_env{env_index}_en.png"
    if legacy_en.is_file():
        return legacy_en
    return primary


def first_existing_env_shot(
    task_id: str, env_count: int
) -> Optional[Tuple[Path, int, str]]:
    """Return ``(shot path, env index, site-relative img path)`` for the first shot found."""
    for env_index in range(env_count):
        shot = task_screenshot_path(task_id, env_index)
        if shot.is_file():
            return shot, env_index, f"img/tasks/{shot.name}"
    return None


def env_image_dim_attr(shot: Path) -> str:
    """Return a width/height attribute string for ``shot`` when dimensions are known."""
    dims = image_dimensions(shot)
    if not dims:
        return ""
    width, height = dims
    return f' width="{width}" height="{height}"'


def theme_title(theme_prefix: str, lang: str) -> str:
    """Return the localized display title for a theme prefix."""
    previous = _set_language(lang)
    try:
        return t(f"help.task_group.{theme_prefix}")
    finally:
        _restore_language(previous)


@dataclass(frozen=True)
class PageAlternateUrls:
    """Canonical and hreflang alternate paths for one page."""

    canonical_path: str
    alternate_en: str
    alternate_ru: str


@dataclass(frozen=True)
class PageMeta:
    """Open Graph, keywords, and structured data for one page."""

    og_type: str = "website"
    og_image_path: Optional[str] = None
    og_image_alt: Optional[str] = None
    keywords: Optional[Sequence[str]] = None
    json_ld: Optional[dict] = None


@dataclass(frozen=True)
class PageLayout:
    """SEO and navigation metadata for one generated HTML page."""

    lang: str
    depth: int
    page_kind: str
    title: str
    description: str
    urls: PageAlternateUrls
    meta: PageMeta = field(default_factory=PageMeta)

    @property
    def canonical_path(self) -> str:
        """Canonical path relative to the site root."""
        return self.urls.canonical_path

    @property
    def alternate_en(self) -> str:
        """English alternate path relative to the site root."""
        return self.urls.alternate_en

    @property
    def alternate_ru(self) -> str:
        """Russian alternate path relative to the site root."""
        return self.urls.alternate_ru

    @property
    def og_image_path(self) -> Optional[str]:
        """Open Graph image path relative to the site root."""
        return self.meta.og_image_path

    @property
    def og_image_alt(self) -> Optional[str]:
        """Open Graph image alt text."""
        return self.meta.og_image_alt

    @property
    def og_type(self) -> str:
        """Open Graph type."""
        return self.meta.og_type

    @property
    def keywords(self) -> Optional[Sequence[str]]:
        """Optional meta keywords."""
        return self.meta.keywords

    @property
    def json_ld(self) -> Optional[dict]:
        """Optional JSON-LD object for the page."""
        return self.meta.json_ld

    @property
    def asset_prefix(self) -> str:
        """Relative prefix for static assets at this page depth."""
        return rel_prefix(self.depth)

    def href(self, relative_to_site_root: str) -> str:
        """Build a same-site href from a path relative to the site root."""
        return f"{self.asset_prefix}{relative_to_site_root}"

    def site_url(self, relative_to_site_root: str) -> str:
        """Build an absolute URL from a path relative to the site root."""
        return absolute_url(relative_to_site_root)


def _set_language(lang: str) -> Optional[str]:
    """Set ``ROBOT_LANGUAGE`` and return the previous value."""
    previous = os.environ.get("ROBOT_LANGUAGE")
    os.environ["ROBOT_LANGUAGE"] = lang
    return previous


def _restore_language(previous: Optional[str]) -> None:
    """Restore ``ROBOT_LANGUAGE`` to ``previous``."""
    if previous is None:
        os.environ.pop("ROBOT_LANGUAGE", None)
    else:
        os.environ["ROBOT_LANGUAGE"] = previous


def localized_constraints(constraints: ScriptConstraints, lang: str) -> List[str]:
    """Return constraint summary lines for ``lang``."""
    previous = _set_language(lang)
    try:
        return constraints_body_lines(constraints)
    finally:
        _restore_language(previous)


def localized_editor_constraint_fields(lang: str) -> List[Tuple[str, str]]:
    """Return ``(ui_label, json_field_name)`` pairs for editor constraint fields."""
    # pylint: disable=import-outside-toplevel,protected-access
    from robot.task_serializer import _CONSTRAINT_FIELD_LABEL_KEYS, _CONSTRAINT_JSON_KEYS

    previous = _set_language(lang)
    try:
        return [
            (t(_CONSTRAINT_FIELD_LABEL_KEYS[field_name]), field_name)
            for field_name in _CONSTRAINT_JSON_KEYS
        ]
    finally:
        _restore_language(previous)


def localized_command_help(lang: str) -> List[Tuple[str, str]]:
    """Return command help ``(signature, description)`` pairs for ``lang``."""
    previous = _set_language(lang)
    try:
        return iter_command_help()
    finally:
        _restore_language(previous)


def render_head(layout: PageLayout) -> str:
    """Render the ``<head>`` block for ``layout``."""
    og_image = layout.og_image_path or "img/hero/intro19_en.webp"
    if layout.lang == "ru" and "_en." in og_image:
        og_image = og_image.replace("_en.", "_ru.", 1)
    og_image_url = layout.site_url(og_image)
    og_alt = escape(layout.og_image_alt or _ui(layout.lang, "og_default_alt"))
    dims = image_dimensions(WEBSITE_DIR / og_image)
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
    keywords_block = ""
    if layout.keywords:
        keywords_text = ", ".join(layout.keywords)
        keywords_block = (
            f'  <meta name="keywords" content="{escape(keywords_text)}">\n'
        )
    canonical_url = escape(layout.site_url(layout.canonical_path))
    return f"""<!DOCTYPE html>
<html lang="{html_lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(layout.title)}</title>
  <meta name="description" content="{escape(layout.description)}">
{keywords_block}  <link rel="canonical" href="{canonical_url}">
  <link rel="alternate" hreflang="en" href="{escape(absolute_url(layout.alternate_en))}">
  <link rel="alternate" hreflang="ru" href="{escape(absolute_url(layout.alternate_ru))}">
  <link rel="alternate" hreflang="x-default" href="{escape(absolute_url(layout.alternate_en))}">
  <meta property="og:title" content="{escape(layout.title)}">
  <meta property="og:description" content="{escape(layout.description)}">
  <meta property="og:type" content="{escape(layout.og_type)}">
  <meta property="og:url" content="{canonical_url}">
  <meta property="og:site_name" content="{escape(_ui(layout.lang, "site_name"))}">
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


def render_site_nav_list(layout: PageLayout) -> str:
    """Render primary navigation list items for ``layout``."""
    nav_items = (
        ("get_started_nav", get_started_href(layout), None),
        ("tasks_nav", layout.href(catalog_relpath(layout.lang)), "catalog"),
        ("commands_nav", layout.href(commands_relpath(layout.lang)), "commands"),
        ("editor_nav", layout.href(editor_relpath(layout.lang)), "editor"),
        ("articles_nav", layout.href(articles_index_relpath(layout.lang)), "articles_index"),
    )
    lines = ['        <ul class="site-nav__list">']
    for key, href, kind in nav_items:
        current = ' aria-current="page"' if kind == layout.page_kind else ""
        label = escape(_ui(layout.lang, key))
        lines.append(f'          <li><a href="{href}"{current}>{label}</a></li>')
    lines.append("        </ul>")
    return "\n".join(lines)


def render_header(layout: PageLayout) -> str:
    """Render the site header and navigation for ``layout``."""
    en_link = layout.href(layout.alternate_en)
    ru_link = layout.href(layout.alternate_ru)
    if layout.lang == "en":
        lang_en_class = ' class="is-active" aria-current="page"'
        lang_ru_class = ""
    else:
        lang_en_class = ""
        lang_ru_class = ' class="is-active" aria-current="page"'
    brand_current = ""
    open_menu_label = escape(_ui(layout.lang, "open_menu"))
    primary_nav_label = escape(_ui(layout.lang, "primary_nav"))
    nav_toggle = (
        '<button type="button" class="nav-toggle" id="nav-toggle" '
        'aria-expanded="false" aria-controls="site-nav" '
        f'aria-label="{open_menu_label}">'
    )
    return f"""  <a class="skip-link" href="#main">{_ui(layout.lang, "skip")}</a>
  <header class="site-header">
    <div class="site-header__inner">
      <a class="brand" href="{layout.href(home_relpath(layout.lang))}"{brand_current}>
        <span class="brand__mark" aria-hidden="true"></span>
        <span class="brand__text">{escape(_ui(layout.lang, "site_name"))}</span>
      </a>
      {nav_toggle}
        <span class="nav-toggle__bar"></span>
        <span class="nav-toggle__bar"></span>
        <span class="nav-toggle__bar"></span>
      </button>
      <nav class="site-nav" id="site-nav" aria-label="{primary_nav_label}">
{render_site_nav_list(layout)}
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
    """Render the site footer for ``layout``."""
    catalog = layout.href(catalog_relpath(layout.lang))
    commands = layout.href(commands_relpath(layout.lang))
    editor = layout.href(editor_relpath(layout.lang))
    github_link = (
        '<a href="https://github.com/step-in-dev/robot" '
        'rel="noopener noreferrer" target="_blank">GitHub</a>'
    )
    releases_link = (
        '<a href="https://github.com/step-in-dev/robot/releases" '
        f'rel="noopener noreferrer" target="_blank">{escape(_ui(layout.lang, "releases"))}</a>'
    )
    footer_brand = (
        f'<p class="site-footer__brand">'
        f'<span class="brand__mark brand__mark--small" aria-hidden="true"></span> '
        f"{escape(_ui(layout.lang, 'footer_tagline'))}</p>"
    )
    return f"""  <footer class="site-footer">
    <div class="site-footer__inner">
      {footer_brand}
      <ul class="site-footer__links">
        <li><a href="{catalog}">{escape(_ui(layout.lang, "tasks_nav"))}</a></li>
        <li><a href="{commands}">{escape(_ui(layout.lang, "commands_nav"))}</a></li>
        <li><a href="{editor}">{escape(_ui(layout.lang, "editor_nav"))}</a></li>
        <li>{github_link}</li>
        <li>{releases_link}</li>
      </ul>
    </div>
  </footer>

  <script src="{layout.href("script.js")}" defer></script>
"""


def render_breadcrumbs(layout: PageLayout, items: Sequence[Tuple[str, str]]) -> str:
    """Render breadcrumb navigation for ``items`` of ``(label, site_path)``."""
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
    """Build schema.org ``BreadcrumbList`` JSON-LD for ``items``."""
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
    """Wrap ``main_html`` in the full page shell for ``layout``."""
    return (
        render_head(layout)
        + "<body>\n"
        + render_header(layout)
        + f'\n  <main id="main" class="content-page">\n{main_html}\n  </main>\n\n'
        + render_footer(layout)
        + "</body>\n</html>\n"
    )


def write_page(path: Path, html_text: str) -> None:
    """Write ``html_text`` to ``path``, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_text, encoding="utf-8")


def first_available_task_image(task_id: str, env_count: int) -> Optional[str]:
    """Return the first existing task screenshot path relative to the site root."""
    found = first_existing_env_shot(task_id, env_count)
    if found is None:
        return None
    return found[2]


def render_environment_figures(
    layout: PageLayout,
    *,
    task_id: str,
    env_count: int,
) -> str:
    """Render environment figure blocks for ``task_id`` when screenshots exist."""
    blocks: List[str] = []
    for env_index in range(env_count):
        shot = task_screenshot_path(task_id, env_index)
        if not shot.is_file():
            continue
        rel = f"img/tasks/{shot.name}"
        alt = escape(
            f"{task_id} – {_ui(layout.lang, 'environment_n', n=env_index + 1)}"
        )
        dim_attr = env_image_dim_attr(shot)
        view_label = escape(
            _ui(layout.lang, "env_view_full", n=env_index + 1)
        )
        caption = escape(
            _ui(layout.lang, "environment_n", n=env_index + 1)
        )
        blocks.append(
            f"""        <figure class="env-figure">
          <button type="button" class="env-figure__open" aria-label="{view_label}">
          <img src="{layout.href(rel)}" alt="{alt}"{dim_attr} loading="lazy">
          </button>
          <figcaption>{caption}</figcaption>
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
