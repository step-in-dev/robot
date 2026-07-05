"""Generate SEO task catalog, command reference, and sitemap for the Robot website."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple, Union
import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# pylint: disable=wrong-import-position
from robot.gui_constraints import task_has_any_constraints
from robot.loader import load_task_definition
from robot.task_catalog import KNOWN_TASK_GROUP_PREFIXES, TaskCatalog

from tools.website_content_data import (
    SITE_BASE,
    SUPPORTED_SITE_LANGS,
    SitemapUrlGroup,
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
    community_pack_anchor_id,
    community_pack_label,
    community_theme_hub_relpath,
    commands_relpath,
    editor_relpath,
    escape,
    first_available_task_image,
    home_relpath,
    load_raw_todo_text,
    localized_constraints,
    normalize_meta_description,
    render_breadcrumbs,
    render_community_pack_download,
    render_environment_figures,
    env_image_dim_attr,
    first_existing_env_shot,
    resolve_todo_text_for_language,
    task_page_filename,
    task_page_relpath,
    theme_hub_relpath,
    theme_title,
    wrap_page,
    write_page,
)
from tools import article_builder
from tools.site_catalog import (
    CommunityPackCatalog,
    SiteTaskCatalog,
    as_site_catalog,
    discover_site_catalog,
)
from tools.website_community_catalog import (
    render_bundled_catalog_card,
    render_community_catalog_sections,
)
from tools.site_reference_pages import build_commands_page, build_editor_page
from tools.site_task_load import load_raw_todo_from_path, load_task_from_path

# pylint: enable=wrong-import-position

__all__ = [
    "build_catalog",
    "build_community_theme_hub",
    "build_commands_page",
    "build_editor_page",
    "build_task_page",
    "build_theme_hub",
    "collect_sitemap_urls",
    "generate_all",
    "write_sitemap",
]

SiteCatalogInput = Union[TaskCatalog, SiteTaskCatalog]


def _theme_display_title(theme_prefix: str, lang: str) -> str:
    """Return localized known theme title or the raw theme id."""
    if theme_prefix in KNOWN_TASK_GROUP_PREFIXES:
        return theme_title(theme_prefix, lang)
    return theme_prefix
def _load_task_definition_for_catalog(catalog: SiteTaskCatalog, task_id: str):
    """Load task definition from bundled tasks or a community pack path."""
    location = catalog.locate_community_task(task_id)
    if location is None:
        return load_task_definition(task_id)
    return load_task_from_path(location.path)


def _load_raw_todo_for_catalog(catalog: SiteTaskCatalog, task_id: str):
    """Load raw ``todoText`` from bundled tasks or a community pack path."""
    location = catalog.locate_community_task(task_id)
    if location is None:
        return load_raw_todo_text(task_id)
    return load_raw_todo_from_path(location.path)


@dataclass(frozen=True)
class _ThemeHubPageSpec:  # pylint: disable=too-many-instance-attributes
    """Inputs that differ between bundled and community theme hub pages."""

    theme_prefix: str
    theme_label: str
    task_ids: Sequence[str]
    depth: int
    canonical: str
    alternate_en: str
    alternate_ru: str
    crumbs: List[Tuple[str, str]]
    pack: Optional[CommunityPackCatalog] = None


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
    depth: int
    theme_prefix: str
    theme_label: str
    canonical: str
    alternate_en: str
    alternate_ru: str
    title: str
    description: str
    og_image: Optional[str]
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
def _community_task_page_crumbs(
    lang: str,
    location,
    theme_label: str,
    task_id: str,
    canonical: str,
) -> List[Tuple[str, str]]:
    """Build breadcrumb items for a community task detail page."""
    return [
        (_ui(lang, "home"), home_relpath(lang)),
        (_ui(lang, "task_catalog"), catalog_relpath(lang)),
        (
            community_pack_label(location.pack.pack_number, location.pack.author, lang),
            f"{catalog_relpath(lang)}#{community_pack_anchor_id(location.pack.prefix)}",
        ),
        (
            theme_label,
            community_theme_hub_relpath(location.pack.prefix, location.theme, lang),
        ),
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
    catalog: SiteTaskCatalog,
    lang: str,
    task_id: str,
    canonical: str,
) -> Tuple[str, List[Tuple[str, str]], str]:
    """Return breadcrumb items and prev/next navigation HTML for a task page."""
    location = catalog.locate_community_task(task_id)
    if location is not None:
        theme_label = _theme_display_title(location.theme, lang)
        crumbs = _community_task_page_crumbs(
            lang,
            location,
            theme_label,
            task_id,
            canonical,
        )
        ids = location.pack.task_ids_for(location.theme)
        return theme_label, crumbs, _task_page_nav_html(ids, ids.index(task_id), lang)
    theme = catalog.bundled.current_theme_for_task(task_id)
    if theme is None:
        raise ValueError(f"Task {task_id!r} not in bundled catalog")
    theme_label = _theme_display_title(theme, lang)
    crumbs = _task_page_crumbs(lang, theme, theme_label, task_id, canonical)
    ids = catalog.bundled.task_ids_for(theme)
    return theme_label, crumbs, _task_page_nav_html(ids, ids.index(task_id), lang)


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
    catalog: SiteTaskCatalog,
    task_id: str,
    lang: str,
) -> _TaskPageParts:
    """Load task metadata and HTML fragments for a task detail page."""
    task_def = _load_task_definition_for_catalog(catalog, task_id)
    todo = resolve_todo_text_for_language(
        _load_raw_todo_for_catalog(catalog, task_id),
        lang,
    ).strip()
    canonical = task_page_relpath(task_id, lang)
    og_image = first_available_task_image(task_id, len(task_def.envs))
    theme_label, crumbs, task_nav = _task_page_navigation(
        catalog, lang, task_id, canonical
    )
    title = f"{task_id} – {theme_label} | {_ui(lang, 'brand_title_suffix')}"
    description = normalize_meta_description(todo or f"Robot task {task_id}.")
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
    catalog: SiteCatalogInput,
    task_id: str,
    lang: str,
) -> str:
    """Render a full HTML page for one task in ``lang``."""
    site = as_site_catalog(catalog)
    parts = _load_task_page_parts(site, task_id, lang)
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


def render_task_list_item(
    layout: PageLayout,
    task_id: str,
    lang: str,
    *,
    task_def=None,
    raw_todo=None,
) -> str:
    """Render one task entry in a theme hub or catalog list."""
    if raw_todo is None:
        raw_todo = load_raw_todo_text(task_id)
    if task_def is None:
        task_def = load_task_definition(task_id)
    todo = resolve_todo_text_for_language(raw_todo, lang)
    snippet = normalize_meta_description(todo, limit=120)
    task_href = layout.href(task_page_relpath(task_id, lang))
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


def render_task_list_item_from_catalog(
    layout: PageLayout,
    catalog: SiteTaskCatalog,
    task_id: str,
    lang: str,
) -> str:
    """Render one task list entry using bundled or community catalog loaders."""
    return render_task_list_item(
        layout,
        task_id,
        lang,
        task_def=_load_task_definition_for_catalog(catalog, task_id),
        raw_todo=_load_raw_todo_for_catalog(catalog, task_id),
    )


def theme_task_id_range(task_ids: Sequence[str]) -> str:
    """Format a compact task id range label such as ``intro1–intro24``."""
    if not task_ids:
        return ""
    if len(task_ids) == 1:
        return task_ids[0]
    return f"{task_ids[0]}\u2013{task_ids[-1]}"


def theme_hub_page_title(theme_label: str, lang: str) -> str:
    """Return the HTML title for a theme hub page."""
    return f"{theme_label} | {_ui(lang, 'brand_title_suffix')}"


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
def theme_hub_og_image(catalog: SiteTaskCatalog, task_ids: Sequence[str]) -> Optional[str]:
    """Return the first available task screenshot for a theme hub OG image."""
    if not task_ids:
        return None
    first_task = task_ids[0]
    task_def = _load_task_definition_for_catalog(catalog, first_task)
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
        depth=parts.depth,
        page_kind="theme",
        title=parts.title,
        description=parts.description,
        urls=PageAlternateUrls(
            canonical_path=parts.canonical,
            alternate_en=parts.alternate_en,
            alternate_ru=parts.alternate_ru,
        ),
        meta=PageMeta(
            og_image_path=parts.og_image,
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


def _bundled_theme_hub_spec(
    catalog: SiteTaskCatalog,
    theme_prefix: str,
    lang: str,
) -> _ThemeHubPageSpec:
    """Build page spec for one bundled theme hub."""
    theme_label = _theme_display_title(theme_prefix, lang)
    canonical = theme_hub_relpath(theme_prefix, lang)
    return _ThemeHubPageSpec(
        theme_prefix=theme_prefix,
        theme_label=theme_label,
        task_ids=catalog.bundled.task_ids_for(theme_prefix),
        depth=2,
        canonical=canonical,
        alternate_en=theme_hub_relpath(theme_prefix, "en"),
        alternate_ru=theme_hub_relpath(theme_prefix, "ru"),
        crumbs=[
            (_ui(lang, "home"), home_relpath(lang)),
            (_ui(lang, "task_catalog"), catalog_relpath(lang)),
            (theme_label, canonical),
        ],
    )


def _community_theme_hub_spec(
    pack: CommunityPackCatalog,
    theme_prefix: str,
    lang: str,
) -> _ThemeHubPageSpec:
    """Build page spec for one community pack theme hub."""
    theme_label = _theme_display_title(theme_prefix, lang)
    canonical = community_theme_hub_relpath(pack.prefix, theme_prefix, lang)
    return _ThemeHubPageSpec(
        theme_prefix=theme_prefix,
        theme_label=theme_label,
        task_ids=pack.task_ids_for(theme_prefix),
        depth=4,
        canonical=canonical,
        alternate_en=community_theme_hub_relpath(pack.prefix, theme_prefix, "en"),
        alternate_ru=community_theme_hub_relpath(pack.prefix, theme_prefix, "ru"),
        crumbs=[
            (_ui(lang, "home"), home_relpath(lang)),
            (_ui(lang, "task_catalog"), catalog_relpath(lang)),
            (
                community_pack_label(pack.pack_number, pack.author, lang),
                f"{catalog_relpath(lang)}#{community_pack_anchor_id(pack.prefix)}",
            ),
            (theme_label, canonical),
        ],
        pack=pack,
    )


def _load_theme_hub_parts(
    catalog: SiteTaskCatalog,
    lang: str,
    layout: PageLayout,
    spec: _ThemeHubPageSpec,
) -> _ThemeHubParts:
    """Load theme hub metadata and list item HTML."""
    title = theme_hub_page_title(spec.theme_label, lang)
    description = theme_hub_meta_description(spec.theme_label, spec.task_ids, lang)
    list_items_html = chr(10).join(
        render_task_list_item_from_catalog(layout, catalog, task_id, lang)
        for task_id in spec.task_ids
    )
    return _ThemeHubParts(
        lang=lang,
        depth=spec.depth,
        theme_prefix=spec.theme_prefix,
        theme_label=spec.theme_label,
        canonical=spec.canonical,
        alternate_en=spec.alternate_en,
        alternate_ru=spec.alternate_ru,
        title=title,
        description=description,
        og_image=theme_hub_og_image(catalog, spec.task_ids),
        task_ids=spec.task_ids,
        crumbs=spec.crumbs,
        list_items_html=list_items_html,
    )


def _theme_hub_body_html(
    layout: PageLayout,
    parts: _ThemeHubParts,
    *,
    pack: Optional[CommunityPackCatalog] = None,
) -> str:
    """Render the article body for a bundled or community theme hub page."""
    tasks_intro = escape(_ui(parts.lang, "tasks_in_theme", count=len(parts.task_ids)))
    catalog_link = layout.href(catalog_relpath(parts.lang))
    catalog_label = escape(_ui(parts.lang, "task_catalog"))
    eyebrow_html = ""
    if pack is not None:
        pack_label = escape(community_pack_label(pack.pack_number, pack.author, parts.lang))
        pack_download = render_community_pack_download(pack.pack.zip_name, parts.lang)
        eyebrow_html = (
            f'        <p class="community-pack__eyebrow">{pack_label}</p>\n'
            f'        <p class="community-pack__download">{pack_download}</p>\n'
        )
    return f"""    <div class="hub-page">
      {render_breadcrumbs(layout, parts.crumbs)}
      <header class="content-header">
{eyebrow_html}        <h1>{escape(parts.theme_label)}</h1>
        <p class="section__intro">{tasks_intro}</p>
      </header>
      <ul class="task-list">
{parts.list_items_html}
      </ul>
      <p class="content-outro"><a href="{catalog_link}">← {catalog_label}</a></p>
    </div>
"""

def _build_theme_hub_page(
    catalog: SiteTaskCatalog,
    lang: str,
    spec: _ThemeHubPageSpec,
) -> str:
    """Render a theme hub page from a bundled or community page spec."""
    layout_stub = PageLayout(
        lang=lang,
        depth=spec.depth,
        page_kind="theme",
        title="",
        description="",
        urls=PageAlternateUrls("", "", ""),
    )
    parts = _load_theme_hub_parts(catalog, lang, layout_stub, spec)
    layout = _theme_hub_layout(parts)
    return wrap_page(layout, _theme_hub_body_html(layout, parts, pack=spec.pack))


def build_theme_hub(catalog: SiteCatalogInput, theme_prefix: str, lang: str) -> str:
    """Render a theme hub page listing all tasks in ``theme_prefix``."""
    site = as_site_catalog(catalog)
    spec = _bundled_theme_hub_spec(site, theme_prefix, lang)
    return _build_theme_hub_page(site, lang, spec)


def build_community_theme_hub(
    catalog: SiteTaskCatalog,
    pack: CommunityPackCatalog,
    theme_prefix: str,
    lang: str,
) -> str:
    """Render a theme hub page listing community tasks from one pack."""
    spec = _community_theme_hub_spec(pack, theme_prefix, lang)
    return _build_theme_hub_page(catalog, lang, spec)


def build_catalog(catalog: SiteCatalogInput, lang: str) -> str:
    """Render the top-level task catalog index page."""
    site = as_site_catalog(catalog)
    canonical = catalog_relpath(lang)
    title = f"{_ui(lang, 'task_catalog')} | {_ui(lang, 'brand_title_suffix')}"
    total = site.total_task_count()
    description = normalize_meta_description(
        _ui(lang, "catalog_meta_description", count=total)
    )
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
    total_label = escape(_ui(lang, "task_count_total", count=total))
    bundled_card = render_bundled_catalog_card(layout, site, lang)
    community_sections = render_community_catalog_sections(layout, site, lang)
    body_html = f"""    <div class="hub-page">
      {render_breadcrumbs(layout, crumbs)}
      <header class="content-header">
        <h1>{escape(_ui(lang, "task_catalog"))}</h1>
        <p class="section__intro">{total_label}</p>
      </header>
      <ul class="theme-card-list">
{bundled_card}
      </ul>
{community_sections}
    </div>
"""
    return wrap_page(layout, body_html)


def collect_sitemap_urls(
    catalog: SiteCatalogInput,
    article_groups: Optional[Sequence[SitemapUrlGroup]] = None,
) -> List[SitemapUrlGroup]:
    """Return sitemap URL groups for alternate-aware pages."""
    site = as_site_catalog(catalog)
    bundled = site.bundled
    groups: List[SitemapUrlGroup] = [
        SitemapUrlGroup(en="index.html", ru="index_ru.html"),
        SitemapUrlGroup(en=commands_relpath("en"), ru=commands_relpath("ru")),
        SitemapUrlGroup(en=editor_relpath("en"), ru=editor_relpath("ru")),
        SitemapUrlGroup(en=catalog_relpath("en"), ru=catalog_relpath("ru")),
    ]
    if article_groups:
        groups.extend(article_groups)
    for theme_prefix in bundled.themes:
        groups.append(
            SitemapUrlGroup(
                en=theme_hub_relpath(theme_prefix, "en"),
                ru=theme_hub_relpath(theme_prefix, "ru"),
            )
        )
    for pack in site.community_packs:
        for theme_prefix in pack.themes:
            groups.append(
                SitemapUrlGroup(
                    en=community_theme_hub_relpath(pack.prefix, theme_prefix, "en"),
                    ru=community_theme_hub_relpath(pack.prefix, theme_prefix, "ru"),
                )
            )
    return groups


def _sitemap_loc(path: str) -> str:
    """Map a sitemap path to its absolute location URL."""
    if path == "index.html":
        return f"{SITE_BASE}/"
    return absolute_url(path)


def _sitemap_url_lines(group: SitemapUrlGroup) -> List[str]:
    """Render one or two ``<url>`` entries for a sitemap group."""
    if group.en and group.ru:
        en_href = _sitemap_loc(group.en)
        ru_href = _sitemap_loc(group.ru)
        lines: List[str] = []
        for loc_path in (group.en, group.ru):
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
        return lines
    if group.en:
        return [
            "  <url>",
            f"    <loc>{_sitemap_loc(group.en)}</loc>",
            "  </url>",
        ]
    if group.ru:
        return [
            "  <url>",
            f"    <loc>{_sitemap_loc(group.ru)}</loc>",
            "  </url>",
        ]
    return []


def write_sitemap(
    catalog: SiteCatalogInput,
    article_groups: Optional[Sequence[SitemapUrlGroup]] = None,
) -> None:
    """Write ``sitemap.xml`` under ``WEBSITE_DIR``."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for group in collect_sitemap_urls(catalog, article_groups=article_groups):
        lines.extend(_sitemap_url_lines(group))
    lines.append("</urlset>")
    (WEBSITE_DIR / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def clean_generated_tasks_dir() -> None:
    """Remove and recreate the generated ``website/tasks`` directory."""
    tasks_dir = WEBSITE_DIR / "tasks"
    if tasks_dir.is_dir():
        shutil.rmtree(tasks_dir)
    tasks_dir.mkdir(parents=True)


def generate_all() -> Tuple[SiteTaskCatalog, list]:
    """Generate all site pages, articles, and the sitemap."""
    catalog = discover_site_catalog()
    bundled = catalog.bundled
    clean_generated_tasks_dir()
    TASKS_IMG_DIR.mkdir(parents=True, exist_ok=True)

    for lang in SUPPORTED_SITE_LANGS:
        write_page(WEBSITE_DIR / commands_relpath(lang), build_commands_page(lang))
        write_page(WEBSITE_DIR / editor_relpath(lang), build_editor_page(lang))
        write_page(WEBSITE_DIR / catalog_relpath(lang), build_catalog(catalog, lang))

    for theme_prefix in bundled.themes:
        for lang in SUPPORTED_SITE_LANGS:
            out = WEBSITE_DIR / theme_hub_relpath(theme_prefix, lang)
            write_page(out, build_theme_hub(catalog, theme_prefix, lang))

    for pack in catalog.community_packs:
        for theme_prefix in pack.themes:
            for lang in SUPPORTED_SITE_LANGS:
                out = WEBSITE_DIR / community_theme_hub_relpath(
                    pack.prefix,
                    theme_prefix,
                    lang,
                )
                write_page(out, build_community_theme_hub(catalog, pack, theme_prefix, lang))

    for theme_prefix in bundled.themes:
        for task_id in bundled.task_ids_for(theme_prefix):
            for lang in SUPPORTED_SITE_LANGS:
                out = WEBSITE_DIR / task_page_relpath(task_id, lang)
                write_page(out, build_task_page(catalog, task_id, lang))

    for task_id in catalog.all_community_task_ids():
        for lang in SUPPORTED_SITE_LANGS:
            out = WEBSITE_DIR / task_page_relpath(task_id, lang)
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
    task_count = catalog.total_task_count()
    theme_hub_count = len(catalog.bundled.themes) + sum(
        len(pack.themes) for pack in catalog.community_packs
    )
    print(
        f"Generated {task_count} task pages × {len(SUPPORTED_SITE_LANGS)} languages, "
        f"{theme_hub_count} theme hubs, command reference, environment editor, "
        f"{len(articles)} article(s), and sitemap."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
