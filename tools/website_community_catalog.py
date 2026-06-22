"""Community pack catalog card rendering for the Robot static site."""

from __future__ import annotations

from typing import List, Sequence, Tuple

from robot.task_catalog import KNOWN_TASK_GROUP_PREFIXES

from tools.site_catalog import CommunityPackCatalog, SiteTaskCatalog
from tools.website_content_layout import (
    PageLayout,
    _ui,
    community_pack_anchor_id,
    community_pack_label,
    community_theme_hub_relpath,
    escape,
    render_community_pack_download,
    theme_task_range_html,
    theme_title,
)


def _theme_display_title(theme_prefix: str, lang: str) -> str:
    """Return localized known theme title or the raw theme id."""
    if theme_prefix in KNOWN_TASK_GROUP_PREFIXES:
        return theme_title(theme_prefix, lang)
    return theme_prefix


def _community_pack_task_groups(
    pack: CommunityPackCatalog,
    layout: PageLayout,
    lang: str,
) -> List[Tuple[str, Sequence[str], str]]:
    """Return community theme groups with already-built hrefs."""
    return [
        (
            theme_prefix,
            pack.task_ids_for(theme_prefix),
            layout.href(
                community_theme_hub_relpath(
                    pack.prefix,
                    theme_prefix,
                    lang,
                )
            ),
        )
        for theme_prefix in pack.themes
    ]


def _render_community_pack_theme_links(
    task_groups: Sequence[Tuple[str, Sequence[str], str]],
    lang: str,
) -> List[str]:
    """Render compact theme links for one community pack card."""
    theme_links: List[str] = []
    for theme_prefix, task_ids, theme_href in task_groups:
        if not task_ids:
            continue
        theme_label = escape(_theme_display_title(theme_prefix, lang))
        range_text = theme_task_range_html(task_ids)
        theme_links.append(
            f"""            <li class="community-pack__theme">
              <a href="{escape(theme_href)}">{theme_label}</a>
              <span class="theme-card__range"> {range_text}</span>
            </li>"""
        )
    return theme_links


def render_community_pack_card(
    pack: CommunityPackCatalog,
    layout: PageLayout,
    lang: str,
) -> str:
    """Render one catalog card for a community pack with theme links inside."""
    pack_heading = escape(community_pack_label(pack.pack_number, pack.author, lang))
    pack_download = render_community_pack_download(pack.pack.zip_name, lang)
    pack_anchor = community_pack_anchor_id(pack.prefix)
    task_groups = _community_pack_task_groups(pack, layout, lang)
    theme_links_html = "\n".join(
        _render_community_pack_theme_links(task_groups, lang)
    )
    return f"""          <li class="theme-card community-pack-card">
            <h2 id="{pack_anchor}">{pack_heading}</h2>
            <p class="community-pack__download">{pack_download}</p>
            <ul class="community-pack__themes">
{theme_links_html}
            </ul>
          </li>"""


def render_community_catalog_sections(
    layout: PageLayout,
    catalog: SiteTaskCatalog,
    lang: str,
) -> str:
    """Render the community section below bundled tasks."""
    sections: List[str] = []
    for pack in catalog.community_packs:
        pack_card = render_community_pack_card(pack, layout, lang)
        sections.append(
            f"""      <section class="community-pack">
        <ul class="theme-card-list">
{pack_card}
        </ul>
      </section>"""
        )
    if not sections:
        return ""
    return f"""      <section class="community-section">
        <h2 class="community-section__heading">{escape(_ui(lang, "community_tasks_heading"))}</h2>
{chr(10).join(sections)}
      </section>"""
