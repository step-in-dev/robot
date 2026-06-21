"""Build article pages from Markdown sources under articles/."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
import re
import shutil
import sys

import markdown
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTICLES_DIR = PROJECT_ROOT / "articles"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# pylint: disable=wrong-import-position
from tools.markdown_front_matter import parse_markdown_front_matter  # noqa: E402
from tools.website_content_data import (  # noqa: E402
    SITE_BASE,
    SUPPORTED_SITE_LANGS,
    WEBSITE_DIR,
)
from tools.website_content_layout import (  # noqa: E402
    PageAlternateUrls,
    PageLayout,
    PageMeta,
    _ui,
    absolute_url,
    articles_index_relpath,
    breadcrumb_json_ld,
    escape,
    home_relpath,
    normalize_meta_description,
    page_filename,
    render_breadcrumbs,
    wrap_page,
    write_page,
)

# pylint: enable=wrong-import-position

_WEBSITE_ASSET_PREFIX = "../../website/"
_IMG_SRC_RE = re.compile(
    r'(?P<attr>(?:src|href))="(?P<url>[^"]+)"',
    flags=re.IGNORECASE,
)
_FIRST_IMG_RE = re.compile(
    r'<img[^>]+src="(?P<src>[^"]+)"',
    flags=re.IGNORECASE,
)

_SITE_LOCALIZED_PAIRS: Tuple[Tuple[str, str], ...] = (
    ("commands.html", "commands_ru.html"),
    ("tasks/index.html", "tasks/index_ru.html"),
)


def _build_site_path_by_lang() -> Dict[str, Dict[str, str]]:
    table: Dict[str, Dict[str, str]] = {}
    for en_path, ru_path in _SITE_LOCALIZED_PAIRS:
        by_lang = {"en": en_path, "ru": ru_path}
        table[en_path] = by_lang
        table[ru_path] = by_lang
    return table


_SITE_PATH_BY_LANG = _build_site_path_by_lang()


@dataclass(frozen=True)
class LocaleContent:
    """Parsed front matter and Markdown body for one article locale."""

    title: str
    description: str
    keywords: Tuple[str, ...]
    body: str


@dataclass
class Article:
    """One article directory with shared metadata and per-locale content."""

    article_id: str
    order: int
    date: str
    author: str
    slug: Dict[str, str]
    locales: Dict[str, LocaleContent] = field(default_factory=dict)
    draft: bool = False

    def slug_for(self, lang: str) -> str:
        """Return the URL slug for ``lang``."""
        return self.slug[lang]

    def locale_path(self, lang: str) -> Path:
        """Return the Markdown source path for ``lang``."""
        return ARTICLES_DIR / self.article_id / f"{lang}.md"

    def page_relpath(self, lang: str) -> str:
        """Return the generated HTML path under ``website/articles/``."""
        slug = self.slug_for(lang)
        return f"articles/{slug}/{page_filename(lang)}"


def _load_article_from_meta(meta_path: Path) -> Optional[Article]:
    """Load one article from ``meta.yaml`` and its locale files; skip drafts."""
    article_id = meta_path.parent.name
    with meta_path.open("r", encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)
    if not isinstance(raw, dict):
        raise SystemExit(f"Invalid meta.yaml in {article_id!r}: expected mapping")
    if bool(raw.get("draft", False)):
        return None
    try:
        order = int(raw["order"])
        article_date = str(raw["date"])
        author = str(raw["author"])
        slug_raw = raw["slug"]
    except KeyError as exc:
        raise SystemExit(
            f"Missing required field {exc.args[0]!r} in {meta_path}"
        ) from exc
    if not isinstance(slug_raw, dict):
        raise SystemExit(f"meta.yaml slug must be a mapping in {article_id!r}")
    slug = {str(k): str(v) for k, v in slug_raw.items()}
    article = Article(
        article_id=article_id,
        order=order,
        date=article_date,
        author=author,
        slug=slug,
    )
    for lang in slug:
        md_path = article.locale_path(lang)
        if not md_path.is_file():
            raise SystemExit(
                f"Missing locale file {md_path.name} for slug.{lang} in {article_id!r}"
            )
        article.locales[lang] = parse_locale_md(md_path)
    return article


def discover_articles(articles_dir: Path = ARTICLES_DIR) -> List[Article]:
    """Return all published articles under ``articles_dir``, highest order first."""
    if not articles_dir.is_dir():
        return []
    articles: List[Article] = []
    for meta_path in sorted(articles_dir.glob("*/meta.yaml")):
        article = _load_article_from_meta(meta_path)
        if article is not None:
            articles.append(article)
    articles.sort(key=lambda item: (-item.order, item.article_id))
    return articles


def validate_articles(articles: Sequence[Article]) -> None:
    """Ensure article orders and per-locale slugs are unique."""
    orders: Dict[int, str] = {}
    slugs_by_lang: Dict[str, Dict[str, str]] = {lang: {} for lang in SUPPORTED_SITE_LANGS}
    for article in articles:
        if article.order in orders:
            raise SystemExit(
                f"Duplicate article order {article.order}: "
                f"{orders[article.order]!r} and {article.article_id!r}"
            )
        orders[article.order] = article.article_id
        for lang, slug in article.slug.items():
            if lang not in SUPPORTED_SITE_LANGS:
                raise SystemExit(
                    f"Unsupported locale {lang!r} in {article.article_id}/meta.yaml"
                )
            existing = slugs_by_lang[lang].get(slug)
            if existing is not None:
                raise SystemExit(
                    f"Duplicate slug {slug!r} for {lang}: "
                    f"{existing!r} and {article.article_id!r}"
                )
            slugs_by_lang[lang][slug] = article.article_id


def parse_locale_md(path: Path) -> LocaleContent:
    """Parse YAML front matter and Markdown body from a locale ``.md`` file."""
    front, body = parse_markdown_front_matter(path, source_label="Locale file")
    try:
        title = str(front["title"])
        description = str(front["description"])
        keywords_raw = front["keywords"]
    except KeyError as exc:
        raise SystemExit(f"Missing front matter field {exc.args[0]!r} in {path}") from exc
    if not isinstance(keywords_raw, list):
        raise SystemExit(f"keywords in {path} must be a list")
    keywords = tuple(str(k) for k in keywords_raw)
    return LocaleContent(
        title=title,
        description=description,
        keywords=keywords,
        body=body,
    )


def markdown_to_html(body: str) -> str:
    """Convert article Markdown body to HTML5."""
    return markdown.markdown(
        body,
        extensions=["tables", "fenced_code", "nl2br"],
        output_format="html5",
    )


def _localized_site_path(path: str, lang: str) -> Optional[str]:
    normalized = path.lstrip("/")
    mapping = _SITE_PATH_BY_LANG.get(normalized)
    if mapping is not None:
        return mapping.get(lang)
    return None


def rewrite_article_html(html_text: str, layout: PageLayout, lang: str) -> str:
    """Rewrite site-root and cross-locale links inside generated article HTML."""
    def replace_attr(match: re.Match[str]) -> str:
        attr = match.group("attr")
        url = match.group("url")
        if url.startswith(_WEBSITE_ASSET_PREFIX):
            site_path = url[len(_WEBSITE_ASSET_PREFIX) :]
            return f'{attr}="{layout.href(site_path)}"'
        if url.startswith(SITE_BASE + "/"):
            rel = url[len(SITE_BASE) + 1 :]
            localized = _localized_site_path(rel, lang)
            if localized is not None:
                return f'{attr}="{layout.href(localized)}"'
        return match.group(0)

    return _IMG_SRC_RE.sub(replace_attr, html_text)


def first_image_path(html_text: str) -> Optional[str]:
    """Return the first ``img/...`` path from article HTML, if any."""
    match = _FIRST_IMG_RE.search(html_text)
    if match is None:
        return None
    src = match.group("src")
    while src.startswith("../"):
        src = src[3:]
    if src.startswith("img/"):
        return src
    return None


def build_article_page(article: Article, lang: str) -> str:
    """Render one localized article page as a full HTML document."""
    locale = article.locales[lang]
    canonical = article.page_relpath(lang)
    depth = 2
    layout = PageLayout(
        lang=lang,
        depth=depth,
        page_kind="article",
        title=locale.title,
        description=normalize_meta_description(locale.description),
        urls=PageAlternateUrls(
            canonical_path=canonical,
            alternate_en=article.page_relpath("en") if "en" in article.slug else canonical,
            alternate_ru=article.page_relpath("ru") if "ru" in article.slug else canonical,
        ),
        meta=PageMeta(
            keywords=locale.keywords,
            og_type="article",
        ),
    )
    body_html = rewrite_article_html(markdown_to_html(locale.body), layout, lang)
    og_image = first_image_path(body_html)
    if og_image:
        layout = replace(layout, meta=replace(layout.meta, og_image_path=og_image))

    crumbs = [
        (_ui(lang, "home"), home_relpath(lang)),
        (_ui(lang, "articles_nav"), articles_index_relpath(lang)),
        (locale.title, canonical),
    ]
    meta_line = escape(f"{article.date} · {article.author}")
    crumb_html = render_breadcrumbs(layout, crumbs)
    main = f"""    <article class="article-page">
      {crumb_html}
      <header class="content-header">
        <h1>{escape(locale.title)}</h1>
        <p class="article-meta">{meta_line}</p>
      </header>
      <div class="article-body">
{body_html}
      </div>
    </article>
"""
    json_ld = {
        "@context": "https://schema.org",
        "@graph": [
            breadcrumb_json_ld(crumbs),
            {
                "@type": "Article",
                "headline": locale.title,
                "description": layout.description,
                "datePublished": article.date,
                "author": {"@type": "Organization", "name": article.author},
                "inLanguage": lang,
                "url": absolute_url(canonical),
            },
        ],
    }
    layout = replace(layout, meta=replace(layout.meta, json_ld=json_ld))
    return wrap_page(layout, main)


def _render_article_list_item(
    article: Article,
    locale: LocaleContent,
    layout: PageLayout,
    lang: str,
) -> str:
    page_path = article.page_relpath(lang)
    href = layout.href(page_path)
    body_html = rewrite_article_html(markdown_to_html(locale.body), layout, lang)
    img_path = first_image_path(body_html)
    img_html = ""
    if img_path:
        img_src = layout.href(img_path)
        img_html = (
            f'              <a class="article-list__thumb-link" href="{escape(href)}">\n'
            f'              <img class="article-list__thumb" src="{escape(img_src)}" '
            f'alt="" loading="lazy" decoding="async">\n'
            f"              </a>\n"
        )
    meta = escape(f"{article.date} · {article.author}")
    snippet = escape(normalize_meta_description(locale.description, limit=200))
    title_link = f'<a href="{escape(href)}">{escape(locale.title)}</a>'
    return f"""          <li class="article-list__item">
            <div class="article-list__layout">
{img_html}              <div class="article-list__body">
                <h2 class="article-list__title">{title_link}</h2>
                <p class="article-list__meta">{meta}</p>
                <p class="article-list__snippet">{snippet}</p>
              </div>
            </div>
          </li>"""


def build_articles_index(articles: Sequence[Article], lang: str) -> str:
    """Render the localized articles index page."""
    canonical = articles_index_relpath(lang)
    page_title = _ui(lang, "articles_page_title")
    heading = _ui(lang, "articles_heading")
    description = normalize_meta_description(_ui(lang, "articles_intro"))
    layout = PageLayout(
        lang=lang,
        depth=1,
        page_kind="articles_index",
        title=page_title,
        description=description,
        urls=PageAlternateUrls(
            canonical_path=canonical,
            alternate_en=articles_index_relpath("en"),
            alternate_ru=articles_index_relpath("ru"),
        ),
    )
    crumbs = [
        (_ui(lang, "home"), home_relpath(lang)),
        (heading, canonical),
    ]
    items: List[str] = []
    for article in articles:
        if lang not in article.locales:
            continue
        locale = article.locales[lang]
        items.append(_render_article_list_item(article, locale, layout, lang))
    if items:
        list_html = "\n".join(items)
    else:
        empty_text = escape(_ui(lang, "articles_empty"))
        list_html = f"          <p>{empty_text}</p>"
    crumb_html = render_breadcrumbs(layout, crumbs)
    main = f"""    <div class="articles-index">
      {crumb_html}
      <header class="content-header">
        <h1>{escape(heading)}</h1>
        <p class="section__intro">{escape(_ui(lang, "articles_intro"))}</p>
      </header>
      <ul class="article-list">
{list_html}
      </ul>
    </div>
"""
    return wrap_page(layout, main)


def clean_generated_articles_dir() -> None:
    """Remove previously generated pages under ``website/articles/``."""
    articles_dir = WEBSITE_DIR / "articles"
    if articles_dir.is_dir():
        shutil.rmtree(articles_dir)


def generate_articles(articles_dir: Path = ARTICLES_DIR) -> List[Article]:
    """Build article index and detail pages into ``website/articles/``."""
    articles = discover_articles(articles_dir)
    validate_articles(articles)
    clean_generated_articles_dir()
    out_root = WEBSITE_DIR / "articles"
    out_root.mkdir(parents=True, exist_ok=True)
    for lang in SUPPORTED_SITE_LANGS:
        index_path = out_root / page_filename(lang)
        write_page(index_path, build_articles_index(articles, lang))
    for article in articles:
        for lang in article.locales:
            out = WEBSITE_DIR / article.page_relpath(lang)
            write_page(out, build_article_page(article, lang))
    return articles


def collect_article_sitemap_groups(
    articles: Sequence[Article],
) -> List[Tuple[str, str]]:
    """Return ``(en_path, ru_path)`` tuples for article sitemap entries."""
    groups: List[Tuple[str, str]] = [
        (articles_index_relpath("en"), articles_index_relpath("ru")),
    ]
    for article in articles:
        if "en" not in article.slug or "ru" not in article.slug:
            continue
        groups.append(
            (
                article.page_relpath("en"),
                article.page_relpath("ru"),
            )
        )
    return groups
