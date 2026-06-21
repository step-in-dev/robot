"""Site-only catalog helpers for bundled and community task packs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import re

from robot.task_catalog import (
    TaskCatalog,
    natural_sort_key,
    ordered_theme_prefixes,
    theme_from_task_id,
)

from tools.build_community_packs import COMMUNITY_DIR, CommunityPack, discover_packs

_PACK_NUMBER_RE = re.compile(r"pack(\d+)$")


def pack_number_from_dir(pack_name: str, fallback_index: int = 1) -> int:
    """Return numeric suffix from ``packN`` or ``fallback_index`` otherwise."""
    match = _PACK_NUMBER_RE.fullmatch(pack_name)
    if match is None:
        return fallback_index
    return int(match.group(1))


@dataclass(frozen=True)
class CommunityPackCatalog:
    """Read-only index of one community pack grouped by theme."""

    pack: CommunityPack
    pack_number: int
    themes: Tuple[str, ...]
    groups: Dict[str, Tuple[str, ...]]
    task_paths: Dict[str, Path]

    @property
    def pack_id(self) -> str:
        """Return the directory name used as internal pack id."""
        return self.pack.directory.name

    @property
    def author(self) -> str:
        """Return pack author from front matter."""
        return self.pack.author

    @property
    def prefix(self) -> str:
        """Return the unique task id prefix for this pack."""
        return self.pack.prefix

    @property
    def directory(self) -> Path:
        """Return community pack directory path."""
        return self.pack.directory

    def task_ids_for(self, prefix: str) -> Tuple[str, ...]:
        """Return sorted task ids for one theme in this pack."""
        return self.groups.get(prefix, ())

    def task_path(self, task_id: str) -> Optional[Path]:
        """Return the absolute ``.env`` path for a community task id."""
        return self.task_paths.get(task_id)

    def all_task_ids(self) -> Tuple[str, ...]:
        """Return all task ids in pack theme order."""
        return tuple(
            task_id
            for theme in self.themes
            for task_id in self.task_ids_for(theme)
        )


@dataclass(frozen=True)
class CommunityTaskLocation:
    """Resolved location metadata for one community task id."""

    pack: CommunityPackCatalog
    theme: str
    path: Path


def _build_community_task_index(
    community_packs: Tuple[CommunityPackCatalog, ...],
) -> Dict[str, CommunityTaskLocation]:
    """Return task id to community location map for fast lookup."""
    index: Dict[str, CommunityTaskLocation] = {}
    for pack in community_packs:
        for theme in pack.themes:
            for task_id in pack.task_ids_for(theme):
                path = pack.task_path(task_id)
                if path is not None:
                    index[task_id] = CommunityTaskLocation(
                        pack=pack,
                        theme=theme,
                        path=path,
                    )
    return index


@dataclass(frozen=True)
class SiteTaskCatalog:
    """Website task catalog with bundled and community sections."""

    bundled: TaskCatalog
    community_packs: Tuple[CommunityPackCatalog, ...]
    community_tasks: Dict[str, CommunityTaskLocation]

    def all_community_task_ids(self) -> Tuple[str, ...]:
        """Return all community task ids in pack/theme/task order."""
        return tuple(
            task_id
            for pack in self.community_packs
            for task_id in pack.all_task_ids()
        )

    def locate_community_task(self, task_id: str) -> Optional[CommunityTaskLocation]:
        """Return pack, theme, and file path for a community task id."""
        return self.community_tasks.get(task_id)

    def total_task_count(self) -> int:
        """Return bundled + community task count."""
        bundled_total = sum(
            len(self.bundled.task_ids_for(theme))
            for theme in self.bundled.themes
        )
        return bundled_total + len(self.community_tasks)


def as_site_catalog(catalog: Union[TaskCatalog, "SiteTaskCatalog"]) -> SiteTaskCatalog:
    """Wrap a bundled-only catalog or return an existing site catalog."""
    if isinstance(catalog, SiteTaskCatalog):
        return catalog
    return SiteTaskCatalog(
        bundled=catalog,
        community_packs=(),
        community_tasks={},
    )


def discover_community_pack_catalog(
    pack: CommunityPack,
    *,
    pack_number: int,
) -> CommunityPackCatalog:
    """Build grouped theme metadata for one community pack."""
    raw_groups: Dict[str, List[str]] = {}
    task_paths: Dict[str, Path] = {}
    for task_path in sorted(pack.directory.glob("*.env")):
        task_id = task_path.stem
        if not task_id.startswith(pack.prefix):
            continue
        stripped_id = task_id[len(pack.prefix) :]
        theme = theme_from_task_id(stripped_id)
        if theme is None:
            continue
        raw_groups.setdefault(theme, []).append(task_id)
        task_paths[task_id] = task_path
    sorted_groups = {
        theme: tuple(sorted(task_ids, key=natural_sort_key))
        for theme, task_ids in raw_groups.items()
        if task_ids
    }
    themes = tuple(ordered_theme_prefixes(raw_groups))
    groups = {theme: sorted_groups[theme] for theme in themes}
    return CommunityPackCatalog(
        pack=pack,
        pack_number=pack_number,
        themes=themes,
        groups=groups,
        task_paths=task_paths,
    )


def discover_site_catalog(
    *,
    bundled_catalog: Optional[TaskCatalog] = None,
    community_dir: Path = COMMUNITY_DIR,
) -> SiteTaskCatalog:
    """Return bundled and community task catalogs for the static site."""
    bundled = bundled_catalog if bundled_catalog is not None else TaskCatalog.discover()
    packs = discover_packs(community_dir)
    community_packs = tuple(
        discover_community_pack_catalog(
            pack,
            pack_number=pack_number_from_dir(pack.directory.name, index),
        )
        for index, pack in enumerate(packs, start=1)
    )
    return SiteTaskCatalog(
        bundled=bundled,
        community_packs=community_packs,
        community_tasks=_build_community_task_index(community_packs),
    )


__all__ = [
    "COMMUNITY_DIR",
    "CommunityPackCatalog",
    "CommunityTaskLocation",
    "SiteTaskCatalog",
    "as_site_catalog",
    "discover_community_pack_catalog",
    "discover_site_catalog",
    "pack_number_from_dir",
]
