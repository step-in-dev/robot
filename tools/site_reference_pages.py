"""Command reference and editor guide pages for the Robot website."""

from __future__ import annotations

from typing import List

from robot.command_help import COMMAND_HELP_SPECS

from tools.website_content_data import (
    COMMAND_GROUP_TITLES,
    COMMAND_GROUPS,
    COMMAND_KEYWORDS,
    EDITOR_CONSTRAINT_DOC_ANCHORS,
    ENV_FORMAT_DOC_BASE,
    GITHUB_RELEASES_URL,
    ONLINE_EDITOR_MAX_COLS,
    ONLINE_EDITOR_MAX_ROWS,
    ONLINE_EDITOR_URL,
)
from tools.website_content_layout import (
    PageAlternateUrls,
    PageLayout,
    PageMeta,
    _ui,
    absolute_url,
    breadcrumb_json_ld,
    commands_relpath,
    editor_relpath,
    escape,
    home_relpath,
    localized_command_help,
    localized_editor_constraint_fields,
    normalize_meta_description,
    render_breadcrumbs,
    wrap_page,
)


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
            json_ld=_tech_article_json_ld(
                crumbs,
                name=_ui(lang, "commands_schema_name"),
                description=description,
                canonical=canonical,
                lang=lang,
            ),
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
    limit_size = escape(
        _ui(
            lang,
            "editor_online_limit_size",
            rows=ONLINE_EDITOR_MAX_ROWS,
            cols=ONLINE_EDITOR_MAX_COLS,
        )
    )
    limit_constraints = escape(_ui(lang, "editor_online_limit_constraints"))
    return f"""      <div class="callout editor-online-card">
        <h3>{escape(_ui(lang, "editor_online_heading"))}</h3>
        <p>{escape(_ui(lang, "editor_online_text"))}</p>
        <ul class="track-list">
        <li>{limit_size}</li>
        <li>{limit_constraints}</li>
        </ul>
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
            json_ld=_tech_article_json_ld(
                crumbs,
                name=_ui(lang, "editor_nav"),
                description=description,
                canonical=canonical,
                lang=lang,
            ),
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


__all__ = ["build_commands_page", "build_editor_page"]


def _tech_article_json_ld(
    crumbs,
    *,
    name: str,
    description: str,
    canonical: str,
    lang: str,
) -> dict:
    """Build shared JSON-LD for simple site reference pages."""
    return {
        "@context": "https://schema.org",
        "@graph": [
            breadcrumb_json_ld(crumbs),
            {
                "@type": "TechArticle",
                "name": name,
                "description": description,
                "inLanguage": lang,
                "url": absolute_url(canonical),
            },
        ],
    }
