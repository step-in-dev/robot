"""Generate SEO task catalog, command reference, and sitemap for the Robot website."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple
import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# pylint: disable=wrong-import-position
from robot.command_help import COMMAND_HELP_SPECS
from robot.gui_constraints import task_has_any_constraints
from robot.loader import load_task_definition
from robot.task_catalog import TaskCatalog

from tools.website_content_data import (
    COMMAND_GROUP_TITLES,
    COMMAND_GROUPS,
    COMMAND_KEYWORDS,
    EDITOR_CONSTRAINT_DOC_ANCHORS,
    ENV_FORMAT_DOC_BASE,
    GITHUB_RELEASES_URL,
    ONLINE_EDITOR_URL,
    SITE_BASE,
    SUPPORTED_SITE_LANGS,
    TASKS_IMG_DIR,
    THEME_HUB_KEYWORDS,
    WEBSITE_DIR,
)
from tools.website_content_layout import (
    PageAlternateUrls,
    PageLayout,
    PageMeta,
    _ui,
    absolute_url,
    breadcrumb_json_ld,
    catalog_relpath,
    commands_relpath,
    editor_relpath,
    escape,
    first_available_task_image,
    home_relpath,
    load_raw_todo_text,
    localized_command_help,
    localized_constraints,
    localized_editor_constraint_fields,
    normalize_meta_description,
    page_filename,
    render_breadcrumbs,
    render_environment_figures,
    env_image_dim_attr,
    first_existing_env_shot,
    resolve_todo_text_for_language,
    task_page_filename,
    task_page_relpath,
    theme_hub_relpath,
    theme_slug,
    theme_title,
    wrap_page,
    write_page,
)
from tools import article_builder

# pylint: enable=wrong-import-position

__all__ = [
    "build_catalog",
    "build_commands_page",
    "build_editor_page",
    "build_task_page",
    "build_theme_hub",
    "collect_sitemap_urls",
    "generate_all",
    "write_sitemap",
]


@dataclass(frozen=True)
class _TaskPageParts:  # pylint: disable=too-many-instance-attributes
    """Collected HTML inputs for one task detail page."""

    task_id: str
    lang: str
    theme_label: str
    title: str
    description: str
    canonical: str
    og_image: Optional[str]
    crumbs: List[Tuple[str, str]]
    todo: str
    env_html: str
    constraints_html: str
    task_nav: str


@dataclass(frozen=True)
class _ThemeHubParts:  # pylint: disable=too-many-instance-attributes
    """Collected HTML inputs for one theme hub page."""

    lang: str
    theme_label: str
    slug: str
    canonical: str
    title: str
    description: str
    task_ids: Sequence[str]
    crumbs: List[Tuple[str, str]]
    list_items_html: str


def _task_page_crumbs(
    lang: str, theme: str, theme_label: str, task_id: str, canonical: str
) -> List[Tuple[str, str]]:
    """Build breadcrumb items for a task detail page."""
    return [
        (_ui(lang, "home"), home_relpath(lang)),
        (_ui(lang, "task_catalog"), catalog_relpath(lang)),
        (theme_label, theme_hub_relpath(theme, lang)),
        (task_id, canonical),
    ]


def _task_page_nav_html(ids: Sequence[str], idx: int, lang: str) -> str:
    """Render prev/next navigation links for a task within its theme."""
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
    if not nav_bits:
        return ""
    return (
        f'<nav class="task-nav" aria-label="Task navigation">'
        f'{" ".join(nav_bits)}</nav>'
    )


def _task_page_constraints_html(task_def, lang: str) -> str:
    """Render the constraints section for a task page, or an empty string."""
    if not task_has_any_constraints(task_def.script_constraints):
        return ""
    lines = localized_constraints(task_def.script_constraints, lang)
    items = "\n".join(f"          <li>{escape(line)}</li>" for line in lines)
    heading = escape(_ui(lang, "constraints_heading"))
    return f"""      <section class="task-constraints" aria-labelledby="constraints-heading">
        <h2 id="constraints-heading">{heading}</h2>
        <ul>
{items}
        </ul>
      </section>
"""


def _task_page_layout(parts: _TaskPageParts) -> PageLayout:
    """Build page metadata for a task detail page."""
    return PageLayout(
        lang=parts.lang,
        depth=1,
        page_kind="task",
        title=parts.title,
        description=parts.description,
        urls=PageAlternateUrls(
            canonical_path=parts.canonical,
            alternate_en=task_page_relpath(parts.task_id, "en"),
            alternate_ru=task_page_relpath(parts.task_id, "ru"),
        ),
        meta=PageMeta(
            robots="noindex, follow",
            og_image_path=parts.og_image,
            json_ld={
                "@context": "https://schema.org",
                "@graph": [
                    breadcrumb_json_ld(parts.crumbs),
                    {
                        "@type": "LearningResource",
                        "name": parts.task_id,
                        "description": parts.description,
                        "inLanguage": parts.lang,
                        "learningResourceType": "problem",
                        "url": absolute_url(parts.canonical),
                    },
                ],
            },
        ),
    )


def _task_page_body_html(layout: PageLayout, parts: _TaskPageParts) -> str:
    """Render the article body for a task detail page."""
    crumb_html = render_breadcrumbs(layout, parts.crumbs)
    todo_html = escape(parts.todo).replace("\n", "<br>\n        ")
    condition_html = (
        f'      <div class="task-condition">{todo_html}</div>\n' if parts.todo else ""
    )
    h1 = (
        f"<code>{escape(parts.task_id)}</code> – "
        f"{escape(parts.theme_label)}"
    )
    example_heading = escape(_ui(parts.lang, "example_heading"))
    showcase = (
        '      <section class="code-showcase" aria-labelledby="example-heading">\n'
        f'        <h2 id="example-heading">{example_heading}</h2>\n'
        '        <pre class="code-block"><code>from robot import *\n\n'
        f'task("{escape(parts.task_id)}")</code></pre>\n'
        "      </section>\n"
    )
    return f"""    <article class="task-page">
      {crumb_html}
      <header class="content-header">
        <h1>{h1}</h1>
      </header>
{condition_html}{parts.env_html}{parts.constraints_html}{showcase}      {parts.task_nav}
    </article>
"""


def _task_page_navigation(
    catalog: TaskCatalog,
    theme: str,
    lang: str,
    task_id: str,
    canonical: str,
) -> Tuple[List[Tuple[str, str]], str]:
    """Return breadcrumb items and prev/next navigation HTML for a task page."""
    theme_label = theme_title(theme, lang)
    crumbs = _task_page_crumbs(lang, theme, theme_label, task_id, canonical)
    ids = catalog.task_ids_for(theme)
    return crumbs, _task_page_nav_html(ids, ids.index(task_id), lang)


def _task_page_env_html(lang: str, task_id: str, env_count: int) -> str:
    """Render environment figures for a task page."""
    layout_stub = PageLayout(
        lang=lang,
        depth=1,
        page_kind="task",
        title="",
        description="",
        urls=PageAlternateUrls("", "", ""),
    )
    return render_environment_figures(
        layout_stub,
        task_id=task_id,
        env_count=env_count,
    )


def _load_task_page_parts(
    catalog: TaskCatalog,
    task_id: str,
    lang: str,
) -> _TaskPageParts:
    """Load task metadata and HTML fragments for a task detail page."""
    theme = catalog.current_theme_for_task(task_id)
    if theme is None:
        raise ValueError(f"Task {task_id!r} not in catalog")
    task_def = load_task_definition(task_id)
    todo = resolve_todo_text_for_language(load_raw_todo_text(task_id), lang).strip()
    theme_label = theme_title(theme, lang)
    title = f"{task_id} – {theme_label} | Robot"
    description = normalize_meta_description(todo or f"Robot task {task_id}.")
    canonical = task_page_relpath(task_id, lang)
    og_image = first_available_task_image(task_id, len(task_def.envs))
    crumbs, task_nav = _task_page_navigation(
        catalog, theme, lang, task_id, canonical
    )
    constraints_html = _task_page_constraints_html(task_def, lang)
    env_html = _task_page_env_html(lang, task_id, len(task_def.envs))
    return _TaskPageParts(
        task_id=task_id,
        lang=lang,
        theme_label=theme_label,
        title=title,
        description=description,
        canonical=canonical,
        og_image=og_image,
        crumbs=crumbs,
        todo=todo,
        env_html=env_html,
        constraints_html=constraints_html,
        task_nav=task_nav,
    )


def build_task_page(
    catalog: TaskCatalog,
    task_id: str,
    lang: str,
) -> str:
    """Render a full HTML page for one task in ``lang``."""
    parts = _load_task_page_parts(catalog, task_id, lang)
    layout = _task_page_layout(parts)
    return wrap_page(layout, _task_page_body_html(layout, parts))


def _task_list_thumbnail(
    layout: PageLayout, task_id: str, lang: str, task_href: str, env_count: int
) -> str:
    """Return thumbnail markup for the first available environment image."""
    found = first_existing_env_shot(task_id, env_count)
    if found is None:
        return ""
    shot, env_index, rel = found
    alt = escape(
        f"{task_id} – {_ui(lang, 'environment_n', n=env_index + 1)}"
    )
    dim_attr = env_image_dim_attr(shot)
    return (
        f'              <a class="task-list__thumb-link" href="{escape(task_href)}">\n'
        f'              <img class="task-list__thumb" src="{layout.href(rel)}" '
        f'alt="{alt}"{dim_attr} loading="lazy" decoding="async">\n'
        f"              </a>\n"
    )


def render_task_list_item(layout: PageLayout, task_id: str, lang: str) -> str:
    """Render one task entry in a theme hub or catalog list."""
    todo = resolve_todo_text_for_language(load_raw_todo_text(task_id), lang)
    snippet = normalize_meta_description(todo, limit=120)
    task_href = layout.href(task_page_relpath(task_id, lang))
    task_def = load_task_definition(task_id)
    img_html = _task_list_thumbnail(
        layout, task_id, lang, task_href, len(task_def.envs)
    )
    snippet_html = ""
    if snippet:
        snippet_html = (
            f'                <p class="task-list__snippet">{escape(snippet)}</p>\n'
        )
    title_link = (
        f'<a href="{escape(task_href)}"><code>{escape(task_id)}</code></a>'
    )
    return f"""          <li class="task-list__item">
            <div class="task-list__layout">
{img_html}              <div class="task-list__body">
                <h2 class="task-list__title">{title_link}</h2>
{snippet_html}              </div>
            </div>
          </li>"""


def theme_task_id_range(task_ids: Sequence[str]) -> str:
    """Format a compact task id range label such as ``intro1–intro24``."""
    if not task_ids:
        return ""
    if len(task_ids) == 1:
        return task_ids[0]
    return f"{task_ids[0]}\u2013{task_ids[-1]}"


def theme_hub_page_title(theme_label: str) -> str:
    """Return the HTML title for a theme hub page."""
    return f"{theme_label} | Robot"


def theme_hub_meta_description(
    theme_label: str, task_ids: Sequence[str], lang: str
) -> str:
    """Build a meta description for a theme hub page."""
    return normalize_meta_description(
        _ui(
            lang,
            "theme_hub_meta_description",
            theme=theme_label,
            count=len(task_ids),
            range=theme_task_id_range(task_ids),
        )
    )


def theme_hub_og_image_alt(theme_label: str, task_ids: Sequence[str], lang: str) -> str:
    """Return Open Graph image alt text for a theme hub page."""
    return _ui(
        lang,
        "theme_hub_og_image_alt",
        theme=theme_label,
        range=theme_task_id_range(task_ids),
    )


def theme_hub_keywords(theme_label: str, lang: str) -> Tuple[str, ...]:
    """Return SEO keywords for a theme hub page."""
    return (theme_label,) + THEME_HUB_KEYWORDS[lang]


def theme_hub_og_image(task_ids: Sequence[str]) -> Optional[str]:
    """Return the first available task screenshot for a theme hub OG image."""
    if not task_ids:
        return None
    first_task = task_ids[0]
    task_def = load_task_definition(first_task)
    return first_available_task_image(first_task, len(task_def.envs))


def _theme_hub_layout(parts: _ThemeHubParts) -> PageLayout:
    """Build page metadata for a theme hub page."""
    item_list = {
        "@type": "ItemList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "url": absolute_url(task_page_relpath(task_id, parts.lang)),
                "name": task_id,
            }
            for index, task_id in enumerate(parts.task_ids, start=1)
        ],
    }
    return PageLayout(
        lang=parts.lang,
        depth=2,
        page_kind="theme",
        title=parts.title,
        description=parts.description,
        urls=PageAlternateUrls(
            canonical_path=parts.canonical,
            alternate_en=f"tasks/{parts.slug}/{page_filename('en')}",
            alternate_ru=f"tasks/{parts.slug}/{page_filename('ru')}",
        ),
        meta=PageMeta(
            og_image_path=theme_hub_og_image(parts.task_ids),
            og_image_alt=theme_hub_og_image_alt(
                parts.theme_label, parts.task_ids, parts.lang
            ),
            keywords=theme_hub_keywords(parts.theme_label, parts.lang),
            json_ld={
                "@context": "https://schema.org",
                "@graph": [
                    breadcrumb_json_ld(parts.crumbs),
                    {
                        "@type": "CollectionPage",
                        "name": parts.theme_label,
                        "description": parts.description,
                        "inLanguage": parts.lang,
                        "url": absolute_url(parts.canonical),
                        "mainEntity": item_list,
                    },
                ],
            },
        ),
    )


def _load_theme_hub_parts(
    catalog: TaskCatalog, theme_prefix: str, lang: str, layout: PageLayout
) -> _ThemeHubParts:
    """Load theme hub metadata and list item HTML."""
    task_ids = catalog.task_ids_for(theme_prefix)
    theme_label = theme_title(theme_prefix, lang)
    slug = theme_slug(theme_prefix)
    canonical = f"tasks/{slug}/{page_filename(lang)}"
    title = theme_hub_page_title(theme_label)
    description = theme_hub_meta_description(theme_label, task_ids, lang)
    crumbs = [
        (_ui(lang, "home"), home_relpath(lang)),
        (_ui(lang, "task_catalog"), catalog_relpath(lang)),
        (theme_label, canonical),
    ]
    list_items_html = chr(10).join(
        render_task_list_item(layout, task_id, lang) for task_id in task_ids
    )
    return _ThemeHubParts(
        lang=lang,
        theme_label=theme_label,
        slug=slug,
        canonical=canonical,
        title=title,
        description=description,
        task_ids=task_ids,
        crumbs=crumbs,
        list_items_html=list_items_html,
    )


def build_theme_hub(catalog: TaskCatalog, theme_prefix: str, lang: str) -> str:
    """Render a theme hub page listing all tasks in ``theme_prefix``."""
    layout_stub = PageLayout(
        lang=lang,
        depth=2,
        page_kind="theme",
        title="",
        description="",
        urls=PageAlternateUrls("", "", ""),
    )
    parts = _load_theme_hub_parts(catalog, theme_prefix, lang, layout_stub)
    layout = _theme_hub_layout(parts)
    tasks_intro = escape(_ui(lang, "tasks_in_theme", count=len(parts.task_ids)))
    catalog_link = layout.href(catalog_relpath(lang))
    catalog_label = escape(_ui(lang, "task_catalog"))
    body_html = f"""    <div class="hub-page">
      {render_breadcrumbs(layout, parts.crumbs)}
      <header class="content-header">
        <h1>{escape(parts.theme_label)}</h1>
        <p class="section__intro">{tasks_intro}</p>
      </header>
      <ul class="task-list">
{parts.list_items_html}
      </ul>
      <p class="content-outro"><a href="{catalog_link}">← {catalog_label}</a></p>
    </div>
"""
    return wrap_page(layout, body_html)


def _catalog_theme_blocks(
    layout: PageLayout, catalog: TaskCatalog, lang: str
) -> List[str]:
    """Render theme summary cards for the catalog index."""
    theme_blocks: List[str] = []
    for theme_prefix in catalog.themes:
        task_ids = catalog.task_ids_for(theme_prefix)
        if not task_ids:
            continue
        theme_label = theme_title(theme_prefix, lang)
        slug = theme_slug(theme_prefix)
        range_text = (
            f"<code>{escape(task_ids[0])}</code> … "
            f"<code>{escape(task_ids[-1])}</code>"
        )
        theme_href = layout.href(f"tasks/{slug}/{page_filename(lang)}")
        theme_blocks.append(
            f"""          <li class="theme-card">
            <h2><a href="{escape(theme_href)}">{escape(theme_label)}</a></h2>
            <p>{range_text}</p>
          </li>"""
        )
    return theme_blocks


def build_catalog(catalog: TaskCatalog, lang: str) -> str:
    """Render the top-level task catalog index page."""
    canonical = catalog_relpath(lang)
    title = f"{_ui(lang, 'task_catalog')} | Robot"
    description = normalize_meta_description(_ui(lang, "catalog_intro"))
    crumbs = [
        (_ui(lang, "home"), home_relpath(lang)),
        (_ui(lang, "task_catalog"), canonical),
    ]

    layout = PageLayout(
        lang=lang,
        depth=1,
        page_kind="catalog",
        title=title,
        description=description,
        urls=PageAlternateUrls(
            canonical_path=canonical,
            alternate_en=catalog_relpath("en"),
            alternate_ru=catalog_relpath("ru"),
        ),
        meta=PageMeta(
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
        ),
    )
    total = sum(len(catalog.task_ids_for(theme)) for theme in catalog.themes)
    intro = escape(_ui(lang, "catalog_intro"))
    total_label = escape(_ui(lang, "task_count_total", count=total))
    body_html = f"""    <div class="hub-page">
      {render_breadcrumbs(layout, crumbs)}
      <header class="content-header">
        <h1>{escape(_ui(lang, "task_catalog"))}</h1>
        <p class="section__intro">{intro} {total_label}</p>
      </header>
      <ul class="theme-card-list">
{chr(10).join(_catalog_theme_blocks(layout, catalog, lang))}
      </ul>
    </div>
"""
    return wrap_page(layout, body_html)


def _command_help_by_key(lang: str) -> dict:
    """Map command keys to localized help descriptions."""
    help_by_key = {key: "" for key, _ in COMMAND_HELP_SPECS}
    for signature, desc in localized_command_help(lang):
        for key, _spec_sig in COMMAND_HELP_SPECS:
            if signature.startswith(key):
                help_by_key[key] = desc
                break
    return help_by_key


def _render_command_groups(lang: str, help_by_key: dict) -> str:
    """Render grouped command reference sections for ``lang``."""
    sig_map = dict(COMMAND_HELP_SPECS)
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
    return chr(10).join(groups_html)


def build_commands_page(lang: str) -> str:
    """Render the command reference page for ``lang``."""
    canonical = commands_relpath(lang)
    title = _ui(lang, "commands_page_title")
    description = normalize_meta_description(_ui(lang, "commands_meta_description"))
    intro_html = _ui(lang, "commands_intro", code="<code>from robot import *</code>")
    crumbs = [
        (_ui(lang, "home"), home_relpath(lang)),
        (_ui(lang, "command_reference"), canonical),
    ]
    help_by_key = _command_help_by_key(lang)
    groups_html = _render_command_groups(lang, help_by_key)

    layout = PageLayout(
        lang=lang,
        depth=0,
        page_kind="commands",
        title=title,
        description=description,
        urls=PageAlternateUrls(
            canonical_path=canonical,
            alternate_en=commands_relpath("en"),
            alternate_ru=commands_relpath("ru"),
        ),
        meta=PageMeta(
            og_image_alt=_ui(lang, "commands_og_image_alt"),
            keywords=COMMAND_KEYWORDS[lang],
            json_ld={
                "@context": "https://schema.org",
                "@graph": [
                    breadcrumb_json_ld(crumbs),
                    {
                        "@type": "TechArticle",
                        "name": _ui(lang, "commands_schema_name"),
                        "description": description,
                        "inLanguage": lang,
                        "url": absolute_url(canonical),
                    },
                ],
            },
        ),
    )
    crumb_html = render_breadcrumbs(layout, crumbs)
    body_html = f"""    <div class="hub-page commands-page">
      {crumb_html}
      <header class="content-header">
        <h1>{escape(_ui(lang, "command_reference"))}</h1>
        <p class="section__intro">{intro_html}</p>
      </header>
      <div class="command-grid">
{groups_html}
      </div>
    </div>
"""
    return wrap_page(layout, body_html)


def _env_format_doc_url(lang: str, anchor: str) -> str:
    """Return a GitHub URL for a section in the task-env-format documentation."""
    return f"{ENV_FORMAT_DOC_BASE[lang]}#{anchor}"


def _releases_link() -> str:
    """Render a link to the module releases page."""
    return (
        f'<a href="{escape(GITHUB_RELEASES_URL)}" rel="noopener noreferrer" '
        f'target="_blank">GitHub Releases</a>'
    )


def _editor_main_figure(layout: PageLayout, lang: str) -> str:
    """Render the editor window screenshot figure."""
    fig_alt = escape(_ui(lang, "editor_fig_editor"))
    editor_img = layout.href("img/editor/editor.webp")
    return f"""          <figure class="inline-figure">
            <img src="{editor_img}" width="846" height="554" alt="{fig_alt}" loading="lazy">
            <figcaption>{fig_alt}</figcaption>
          </figure>"""


def _render_editor_steps(layout: PageLayout, lang: str) -> str:
    """Render numbered editor guide steps with figures."""
    example_task = escape(_ui(lang, "editor_example_task"))
    step_1 = escape(_ui(lang, "editor_step_1", link="{link}")).replace(
        "{link}", _releases_link()
    )
    return f"""      <ol class="editor-steps">
        <li>
          <p>{step_1}</p>
          <pre class="code-block"><code>python editor/editor.py</code></pre>
        </li>
        <li>
          <p>{escape(_ui(lang, "editor_step_2"))}</p>
{_editor_main_figure(layout, lang)}
        </li>
        <li>
          <p>{escape(_ui(lang, "editor_step_3"))}</p>
        </li>
        <li>
          <p>{escape(_ui(lang, "editor_step_4"))}</p>
          <pre class="code-block"><code>from robot import *

task("{example_task}")</code></pre>
        </li>
      </ol>"""


def _render_editor_constraints_note(lang: str) -> str:
    """Render the solution-constraints list for the editor page callout."""
    items: List[str] = []
    for label, field_name in localized_editor_constraint_fields(lang):
        anchor = EDITOR_CONSTRAINT_DOC_ANCHORS[lang][field_name]
        doc_url = escape(_env_format_doc_url(lang, anchor))
        items.append(
            f"        <li>{escape(label)} ("
            f'<a href="{doc_url}" rel="noopener noreferrer" target="_blank">'
            f"<code>{escape(field_name)}</code></a>)</li>"
        )
    items_html = "\n".join(items)
    return f"""        <p>{escape(_ui(lang, "editor_note_p2_intro"))}</p>
        <ul class="track-list">
{items_html}
        </ul>"""


def _render_editor_online_card(lang: str) -> str:
    """Render the online environment editor promo card."""
    url = escape(ONLINE_EDITOR_URL[lang])
    link_text = escape(_ui(lang, "editor_online_link"))
    return f"""      <div class="callout editor-online-card">
        <h3>{escape(_ui(lang, "editor_online_heading"))}</h3>
        <p>{escape(_ui(lang, "editor_online_text"))}</p>
        <p><a href="{url}" rel="noopener noreferrer" target="_blank">{link_text}</a></p>
      </div>"""


def build_editor_page(lang: str) -> str:
    """Render the environment editor guide page for ``lang``."""
    canonical = editor_relpath(lang)
    title = f"{_ui(lang, 'editor_nav')} | Robot"
    description = normalize_meta_description(_ui(lang, "editor_intro"))
    crumbs = [
        (_ui(lang, "home"), home_relpath(lang)),
        (_ui(lang, "editor_nav"), canonical),
    ]

    layout = PageLayout(
        lang=lang,
        depth=0,
        page_kind="editor",
        title=title,
        description=description,
        urls=PageAlternateUrls(
            canonical_path=canonical,
            alternate_en=editor_relpath("en"),
            alternate_ru=editor_relpath("ru"),
        ),
        meta=PageMeta(
            json_ld={
                "@context": "https://schema.org",
                "@graph": [
                    breadcrumb_json_ld(crumbs),
                    {
                        "@type": "TechArticle",
                        "name": _ui(lang, "editor_nav"),
                        "description": description,
                        "inLanguage": lang,
                        "url": absolute_url(canonical),
                    },
                ],
            },
        ),
    )
    crumb_html = render_breadcrumbs(layout, crumbs)
    steps_html = _render_editor_steps(layout, lang)
    constraints_note_html = _render_editor_constraints_note(lang)
    online_card_html = _render_editor_online_card(lang)
    body_html = f"""    <div class="hub-page editor-page">
      {crumb_html}
      <header class="content-header">
        <h1>{escape(_ui(lang, "editor_nav"))}</h1>
        <p class="section__intro">{escape(_ui(lang, "editor_intro"))}</p>
      </header>
{steps_html}
      <div class="callout">
        <h3>{escape(_ui(lang, "editor_note_heading"))}</h3>
        <p>{escape(_ui(lang, "editor_note_p1"))}</p>
{constraints_note_html}
      </div>
{online_card_html}
    </div>
"""
    return wrap_page(layout, body_html)


def collect_sitemap_urls(
    catalog: TaskCatalog,
    article_groups: Optional[Sequence[Tuple[str, str]]] = None,
) -> List[Tuple[str, str]]:
    """Return (en_path, ru_path) tuples for alternate URL groups."""
    groups: List[Tuple[str, str]] = [
        ("index.html", "index_ru.html"),
        (commands_relpath("en"), commands_relpath("ru")),
        (editor_relpath("en"), editor_relpath("ru")),
        (catalog_relpath("en"), catalog_relpath("ru")),
    ]
    if article_groups:
        groups.extend(article_groups)
    for theme_prefix in catalog.themes:
        slug = theme_slug(theme_prefix)
        groups.append(
            (
                f"tasks/{slug}/index.html",
                f"tasks/{slug}/index_ru.html",
            )
        )
    return groups


def _sitemap_loc(path: str) -> str:
    """Map a sitemap path to its absolute location URL."""
    if path == "index.html":
        return f"{SITE_BASE}/"
    return absolute_url(path)


def write_sitemap(
    catalog: TaskCatalog,
    article_groups: Optional[Sequence[Tuple[str, str]]] = None,
) -> None:
    """Write ``sitemap.xml`` under ``WEBSITE_DIR``."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for en_path, ru_path in collect_sitemap_urls(
        catalog, article_groups=article_groups
    ):
        en_href = _sitemap_loc(en_path)
        ru_href = _sitemap_loc(ru_path)
        for loc_path in (en_path, ru_path):
            lines.extend(
                [
                    "  <url>",
                    f"    <loc>{_sitemap_loc(loc_path)}</loc>",
                    f'    <xhtml:link rel="alternate" hreflang="en" href="{en_href}"/>',
                    f'    <xhtml:link rel="alternate" hreflang="ru" href="{ru_href}"/>',
                    f'    <xhtml:link rel="alternate" hreflang="x-default" href="{en_href}"/>',
                    "  </url>",
                ]
            )
    lines.append("</urlset>")
    (WEBSITE_DIR / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def clean_generated_tasks_dir() -> None:
    """Remove and recreate the generated ``website/tasks`` directory."""
    tasks_dir = WEBSITE_DIR / "tasks"
    if tasks_dir.is_dir():
        shutil.rmtree(tasks_dir)
    tasks_dir.mkdir(parents=True)


def generate_all() -> Tuple[TaskCatalog, list]:
    """Generate all site pages, articles, and the sitemap."""
    catalog = TaskCatalog.discover()
    clean_generated_tasks_dir()
    TASKS_IMG_DIR.mkdir(parents=True, exist_ok=True)

    for lang in SUPPORTED_SITE_LANGS:
        write_page(WEBSITE_DIR / commands_relpath(lang), build_commands_page(lang))
        write_page(WEBSITE_DIR / editor_relpath(lang), build_editor_page(lang))
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

    articles = article_builder.generate_articles()
    article_groups = article_builder.collect_article_sitemap_groups(articles)
    write_sitemap(catalog, article_groups=article_groups)
    return catalog, articles


def main() -> int:
    """CLI entry point for the website content generator."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    catalog, articles = generate_all()
    task_count = sum(len(catalog.task_ids_for(t)) for t in catalog.themes)
    print(
        f"Generated {task_count} task pages × {len(SUPPORTED_SITE_LANGS)} languages, "
        f"{len(catalog.themes)} theme hubs, command reference, environment editor, "
        f"{len(articles)} article(s), and sitemap."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
