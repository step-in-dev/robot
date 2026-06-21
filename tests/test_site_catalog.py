"""Tests for site-only bundled/community catalog discovery."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.loader_runtime._helpers import write_minimal_task_env
from tools.site_catalog import (
    COMMUNITY_DIR,
    discover_community_pack_catalog,
    discover_site_catalog,
    pack_number_from_dir,
)
from tools.build_community_packs import load_pack_metadata


def _write_pack(
    community_dir: Path,
    pack_name: str,
    *,
    prefix: str,
    author: str = "Test Author",
    task_ids: tuple[str, ...] = ("xintro1",),
) -> Path:
    """Create a temporary community pack directory with minimal task files."""
    pack_dir = community_dir / pack_name
    pack_dir.mkdir(parents=True)
    front_matter = [
        "---",
        f'author: "{author}"',
        f'prefix: "{prefix}"',
        "---",
        "",
    ]
    (pack_dir / "readme.md").write_text(
        "\n".join(front_matter),
        encoding="utf-8",
    )
    for task_id in task_ids:
        write_minimal_task_env(pack_dir / f"{task_id}.env", task_id)
    return pack_dir


class PackNumberFromDirTest(unittest.TestCase):
    def test_reads_numeric_suffix(self) -> None:
        self.assertEqual(pack_number_from_dir("pack12"), 12)

    def test_uses_fallback_for_nonstandard_name(self) -> None:
        self.assertEqual(pack_number_from_dir("extra", 7), 7)


class DiscoverCommunityPackCatalogTest(unittest.TestCase):
    def test_groups_by_theme_without_pack_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            community_dir = Path(temp_dir) / "community"
            pack_dir = _write_pack(
                community_dir,
                "pack1",
                prefix="t",
                task_ids=("tintro10", "tintro2", "tcustom9", "treadme"),
            )
            pack = load_pack_metadata(pack_dir)

            catalog = discover_community_pack_catalog(pack, pack_number=1)

        self.assertEqual(catalog.pack_number, 1)
        self.assertEqual(catalog.prefix, "t")
        self.assertEqual(catalog.themes, ("intro", "custom"))
        self.assertEqual(catalog.task_ids_for("intro"), ("tintro2", "tintro10"))
        self.assertEqual(catalog.task_ids_for("custom"), ("tcustom9",))
        self.assertIsNone(catalog.task_path("missing"))
        self.assertTrue(str(catalog.task_path("tintro2")).endswith("tintro2.env"))
        self.assertNotIn("treadme", catalog.all_task_ids())

    def test_site_catalog_locates_real_pack1_task(self) -> None:
        if not (COMMUNITY_DIR / "pack1").is_dir():
            self.skipTest("community/pack1 not present")

        site_catalog = discover_site_catalog()
        location = site_catalog.locate_community_task("rintro1")

        self.assertIsNotNone(location)
        assert location is not None
        self.assertEqual(location.pack.pack_id, "pack1")
        self.assertEqual(location.pack.pack_number, 1)
        self.assertEqual(location.pack.author, "Александр Родюшкин")
        self.assertEqual(location.theme, "intro")
        self.assertEqual(location.path.name, "rintro1.env")
        self.assertIn("rintro1", site_catalog.all_community_task_ids())


if __name__ == "__main__":
    unittest.main()
