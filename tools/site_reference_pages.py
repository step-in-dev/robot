"""Command reference and editor guide pages for the Robot website."""

from __future__ import annotations

from typing import List, Sequence, Tuple

from robot.command_help import COMMAND_HELP_SPECS

from tools.website_content_data import (
    COMMAND_GROUP_TITLES,
    COMMAND_GROUPS,
    COMMAND_KEYWORDS,
    EDITOR_CONSTRAINT_DOC_ANCHORS,
    ENV_FORMAT_DOC_BASE,
    FIELD_LEGEND_HEIGHT,
    FIELD_LEGEND_IMAGE,
    FIELD_LEGEND_ITEMS,
    FIELD_LEGEND_LABEL_GAP,
    FIELD_LEGEND_LINE_CLASS,
    FIELD_LEGEND_PADDING,
    FIELD_LEGEND_TEXT_CLASS,
    FIELD_LEGEND_WIDTH,
    FieldLegendItem,
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
    help_by_key = dict.fromkeys((key for key, _ in COMMAND_HELP_SPECS), "")
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


_FIELD_LEGEND_TITLE_ID = "field-legend-title"
_FIELD_LEGEND_FONT_SIZE = 13
_FIELD_LEGEND_TEXT_LINE_HEIGHT = 16
_FIELD_LEGEND_TEXT_SPACE_WIDTH = 3.6
_FIELD_LEGEND_TEXT_PUNCT_WIDTH = 4.5
_FIELD_LEGEND_TEXT_CHAR_WIDTH = 7.1
_FIELD_LEGEND_TEXT_CAP_WIDTH = 7.8
_FIELD_LEGEND_CONNECTOR_GAP = 10
_FIELD_LEGEND_SIDE_BEND = 28
_LegendPoint = Tuple[float, float]
_LegendBox = Tuple[float, float, float, float]


def _field_legend_viewbox_size() -> Tuple[int, int]:
    padding = FIELD_LEGEND_PADDING
    width = padding["left"] + FIELD_LEGEND_WIDTH + padding["right"]
    height = padding["top"] + FIELD_LEGEND_HEIGHT + padding["bottom"]
    return width, height


def _field_legend_label_lines(lang: str, item_id: str) -> Sequence[str]:
    raw = _ui(lang, f"commands_field_legend_{item_id}")
    return tuple(line for line in raw.split("\n") if line)


def _field_legend_text_anchor(side: str) -> str:
    if side == "left":
        return "end"
    if side == "right":
        return "start"
    return "middle"


def _field_legend_measure_text(line: str) -> float:
    """Approximate one legend label line width in SVG user units."""
    width = 0.0
    for char in line:
        if char == " ":
            width += _FIELD_LEGEND_TEXT_SPACE_WIDTH
        elif char in "().,-":
            width += _FIELD_LEGEND_TEXT_PUNCT_WIDTH
        elif char.isupper():
            width += _FIELD_LEGEND_TEXT_CAP_WIDTH
        else:
            width += _FIELD_LEGEND_TEXT_CHAR_WIDTH
    return width


def _field_legend_text_metrics(lines: Sequence[str]) -> Tuple[float, float]:
    """Return approximated width and height of one label block."""
    line_count = max(1, len(lines))
    return (
        max((_field_legend_measure_text(line) for line in lines), default=0.0),
        line_count * _FIELD_LEGEND_TEXT_LINE_HEIGHT,
    )


def _field_legend_text_box(
    *,
    text_x: float,
    text_y: float,
    text_anchor: str,
    text_width: float,
    text_height: float,
) -> _LegendBox:
    """Return the approximated bounding box of a legend label block."""
    if text_anchor == "end":
        left = text_x - text_width
        right = text_x
    elif text_anchor == "start":
        left = text_x
        right = text_x + text_width
    else:
        half_width = text_width * 0.5
        left = text_x - half_width
        right = text_x + half_width
    half_height = text_height * 0.5
    return left, text_y - half_height, right, text_y + half_height


def _field_legend_connector_edge_x(
    *,
    target_x: float,
    left: float,
    right: float,
) -> float:
    """Return the x coordinate where the connector should leave the text box."""
    if target_x <= left:
        return left - _FIELD_LEGEND_CONNECTOR_GAP
    if target_x >= right:
        return right + _FIELD_LEGEND_CONNECTOR_GAP
    if (target_x - left) <= (right - target_x):
        return left - _FIELD_LEGEND_CONNECTOR_GAP
    return right + _FIELD_LEGEND_CONNECTOR_GAP


def _field_legend_text_position(
    item: FieldLegendItem,
    *,
    anchor: _LegendPoint,
    image_origin: Tuple[int, int],
    text_block_height: float,
) -> _LegendPoint:
    """Return the label position for one legend item."""
    abs_x, abs_y = anchor
    img_x, img_y = image_origin
    if item.side == "left":
        return (
            img_x - FIELD_LEGEND_LABEL_GAP + item.label_dx,
            abs_y + item.label_dy,
        )
    if item.side == "right":
        return (
            img_x + FIELD_LEGEND_WIDTH + FIELD_LEGEND_LABEL_GAP + item.label_dx,
            abs_y + item.label_dy,
        )
    if item.side == "top":
        return (
            abs_x + item.label_dx,
            img_y - FIELD_LEGEND_LABEL_GAP - text_block_height * 0.5 + item.label_dy,
        )
    return (
        abs_x + item.label_dx,
        img_y
        + FIELD_LEGEND_HEIGHT
        + FIELD_LEGEND_LABEL_GAP
        + text_block_height * 0.5
        + item.label_dy,
    )


def _field_legend_connector_points(
    item: FieldLegendItem,
    *,
    anchor: _LegendPoint,
    text_box: _LegendBox,
) -> Tuple[_LegendPoint, ...]:
    """Return the connector polyline points for one legend item."""
    abs_x, abs_y = anchor
    left, top, right, bottom = text_box
    text_mid_y = (top + bottom) * 0.5
    if item.side == "left":
        start_x = right + _FIELD_LEGEND_CONNECTOR_GAP
        if abs(text_mid_y - abs_y) < 0.5:
            return ((start_x, abs_y), (abs_x, abs_y), (abs_x, abs_y))
        bend_x = min(start_x + _FIELD_LEGEND_SIDE_BEND, abs_x - _FIELD_LEGEND_CONNECTOR_GAP)
        return ((start_x, text_mid_y), (bend_x, text_mid_y), (abs_x, abs_y))
    if item.side == "right":
        start_x = left - _FIELD_LEGEND_CONNECTOR_GAP
        if abs(text_mid_y - abs_y) < 0.5:
            return ((start_x, abs_y), (abs_x, abs_y), (abs_x, abs_y))
        bend_x = max(start_x - _FIELD_LEGEND_SIDE_BEND, abs_x + _FIELD_LEGEND_CONNECTOR_GAP)
        return ((start_x, text_mid_y), (bend_x, text_mid_y), (abs_x, abs_y))
    connector_x = _field_legend_connector_edge_x(
        target_x=abs_x,
        left=left,
        right=right,
    )
    elbow_y = text_mid_y + item.connector_dy
    return (
        (connector_x, elbow_y),
        (abs_x, elbow_y),
        (abs_x, abs_y),
    )


def _field_legend_geometry(
    item: FieldLegendItem,
    *,
    img_x: int,
    img_y: int,
    lines: Sequence[str],
) -> Tuple[float, float, str, Tuple[_LegendPoint, ...]]:
    """Return text position, text-anchor, and connector points for one item."""
    anchor = (img_x + item.ax, img_y + item.ay)
    text_anchor = _field_legend_text_anchor(item.side)
    text_block_width, text_block_height = _field_legend_text_metrics(lines)
    text_x, text_y = _field_legend_text_position(
        item,
        anchor=anchor,
        image_origin=(img_x, img_y),
        text_block_height=text_block_height,
    )

    text_box = _field_legend_text_box(
        text_x=text_x,
        text_y=text_y,
        text_anchor=text_anchor,
        text_width=text_block_width,
        text_height=text_block_height,
    )
    connector_points = _field_legend_connector_points(
        item,
        anchor=anchor,
        text_box=text_box,
    )

    return text_x, text_y, text_anchor, connector_points


def _render_field_legend_text(
    *,
    item_id: str,
    text_x: float,
    text_y: float,
    lines: Sequence[str],
    text_anchor: str,
) -> str:
    if not lines:
        return ""
    if len(lines) == 1:
        return (
            f'        <text x="{text_x:.1f}" y="{text_y:.1f}" '
            f'text-anchor="{text_anchor}" dominant-baseline="middle" '
            f'font-size="{_FIELD_LEGEND_FONT_SIZE}" data-field-legend-item="{item_id}" '
            f'class="{FIELD_LEGEND_TEXT_CLASS}">'
            f"{escape(lines[0])}</text>"
        )

    first_y = text_y - (len(lines) - 1) * _FIELD_LEGEND_TEXT_LINE_HEIGHT * 0.5
    parts = [
        f'        <text x="{text_x:.1f}" text-anchor="{text_anchor}" '
        f'dominant-baseline="middle" font-size="{_FIELD_LEGEND_FONT_SIZE}" '
        f'data-field-legend-item="{item_id}" class="{FIELD_LEGEND_TEXT_CLASS}">'
    ]
    for index, line in enumerate(lines):
        line_y = first_y + index * _FIELD_LEGEND_TEXT_LINE_HEIGHT
        parts.append(
            f'<tspan x="{text_x:.1f}" y="{line_y:.1f}">'
            f"{escape(line)}</tspan>"
        )
    parts.append("</text>")
    return "".join(parts)


def _render_field_legend_connector(
    item_id: str,
    connector_points: Tuple[_LegendPoint, ...],
) -> str:
    """Render one polyline connector for a legend item."""
    points_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y in connector_points)
    return (
        f'          <polyline points="{points_attr}"'
        f' data-field-legend-item="{item_id}" class="{FIELD_LEGEND_LINE_CLASS}"/>'
    )


def _render_field_legend_item(
    item: FieldLegendItem,
    *,
    lang: str,
    img_x: int,
    img_y: int,
) -> Tuple[str, str]:
    lines = _field_legend_label_lines(lang, item.item_id)
    text_x, text_y, text_anchor, connector_points = (
        _field_legend_geometry(
            item,
            img_x=img_x,
            img_y=img_y,
            lines=lines,
        )
    )
    return (
        _render_field_legend_connector(item.item_id, connector_points),
        _render_field_legend_text(
            item_id=item.item_id,
            text_x=text_x,
            text_y=text_y,
            lines=lines,
            text_anchor=text_anchor,
        ),
    )


def _render_field_legend(layout: PageLayout, lang: str) -> str:
    """Render the annotated field diagram for the commands reference page."""
    padding = FIELD_LEGEND_PADDING
    img_x = padding["left"]
    img_y = padding["top"]
    view_w, view_h = _field_legend_viewbox_size()
    image_href = escape(layout.href(FIELD_LEGEND_IMAGE))
    title = escape(_ui(lang, "commands_field_legend_title"))

    parts: List[str] = [
        '      <figure class="field-legend">',
        '        <svg class="field-legend__svg" xmlns="http://www.w3.org/2000/svg"',
        f' viewBox="0 0 {view_w} {view_h}" width="{view_w}" height="{view_h}"',
        f' role="img" aria-labelledby="{_FIELD_LEGEND_TITLE_ID}">',
        f'          <title id="{_FIELD_LEGEND_TITLE_ID}">{title}</title>',
        f'          <image href="{image_href}" x="{img_x}" y="{img_y}"',
        f' width="{FIELD_LEGEND_WIDTH}" height="{FIELD_LEGEND_HEIGHT}"/>',
    ]
    connector_parts: List[str] = []
    text_parts: List[str] = []

    for item in FIELD_LEGEND_ITEMS:
        connector_html, text_html = _render_field_legend_item(
            item,
            lang=lang,
            img_x=img_x,
            img_y=img_y,
        )
        connector_parts.append(connector_html)
        text_parts.append(text_html)

    parts.extend(connector_parts)
    parts.extend(text_parts)
    parts.extend(["        </svg>", "      </figure>"])
    return "\n".join(parts)


def build_commands_page(lang: str) -> str:
    """Render the command reference page for ``lang``."""
    canonical = commands_relpath(lang)
    title = f"{_ui(lang, 'commands_page_title')} | {_ui(lang, 'brand_title_suffix')}"
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
    legend_html = _render_field_legend(layout, lang)
    completion_html = escape(_ui(lang, "commands_field_legend_completion"))
    body_html = f"""    <div class="hub-page commands-page">
      {crumb_html}
      <header class="content-header">
        <h1>{escape(_ui(lang, "command_reference"))}</h1>
        <p class="section__intro">{intro_html}</p>
      </header>
{legend_html}
      <p class="section__intro">{completion_html}</p>
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
    title = f"{_ui(lang, 'editor_nav')} | {_ui(lang, 'brand_title_suffix')}"
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
