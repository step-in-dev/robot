"""Tests for community task pack release archives."""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.build_community_packs import (
    COMMUNITY_DIR,
    build_all_community_packs,
    build_pack_zip,
    discover_packs,
    load_pack_metadata,
)


def _write_pack(
    community_dir: Path,
    pack_name: str,
    *,
    prefix: str,
    author: str = "Test Author",
    env_names: tuple[str, ...] = ("xintro1.env",),
) -> Path:
    pack_dir = community_dir / pack_name
    pack_dir.mkdir(parents=True)
    readme = (
        "---\n"
        f'author: "{author}"\n'
        f'prefix: "{prefix}"\n'
        "---\n"
    )
    (pack_dir / "readme.md").write_text(readme, encoding="utf-8")
    for env_name in env_names:
        (pack_dir / env_name).write_text("{}", encoding="utf-8")
    return pack_dir


class BuildCommunityPacksTest(unittest.TestCase):
    def test_builds_zip_with_flat_files_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            community_dir = root / "community"
            output_dir = root / "out"
            pack_dir = _write_pack(
                community_dir,
                "pack1",
                prefix="t",
                env_names=("tintro1.env", "tintro2.env"),
            )
            nested = pack_dir / "nested"
            nested.mkdir()
            (nested / "skip.env").write_text("{}", encoding="utf-8")

            pack = load_pack_metadata(pack_dir)
            zip_path = build_pack_zip(pack, output_dir)

            self.assertEqual(zip_path.name, "ttasks.zip")
            with zipfile.ZipFile(zip_path) as archive:
                names = set(archive.namelist())
            self.assertEqual(
                names,
                {"readme_t.md", "tintro1.env", "tintro2.env"},
            )

    def test_duplicate_prefix_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            community_dir = Path(temp_dir) / "community"
            _write_pack(community_dir, "pack1", prefix="dup")
            _write_pack(community_dir, "pack2", prefix="dup")

            with self.assertRaises(SystemExit) as ctx:
                discover_packs(community_dir)
            self.assertIn("Duplicate pack prefix", str(ctx.exception))

    def test_missing_readme_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack_dir = Path(temp_dir) / "community" / "pack1"
            pack_dir.mkdir(parents=True)
            (pack_dir / "only.env").write_text("{}", encoding="utf-8")

            with self.assertRaises(SystemExit) as ctx:
                load_pack_metadata(pack_dir)
            self.assertIn("Missing readme.md", str(ctx.exception))

    def test_invalid_front_matter_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack_dir = Path(temp_dir) / "community" / "pack1"
            pack_dir.mkdir(parents=True)
            (pack_dir / "readme.md").write_text("no front matter\n", encoding="utf-8")

            with self.assertRaises(SystemExit) as ctx:
                load_pack_metadata(pack_dir)
            self.assertIn("YAML front matter", str(ctx.exception))

    def test_pack1_smoke_build(self) -> None:
        if not (COMMUNITY_DIR / "pack1").is_dir():
            self.skipTest("community/pack1 not present")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            paths = build_all_community_packs(
                output_dir,
                community_dir=COMMUNITY_DIR,
            )

            self.assertEqual(len(paths), 1)
            self.assertEqual(paths[0].name, "rtasks.zip")
            with zipfile.ZipFile(paths[0]) as archive:
                names = archive.namelist()
            self.assertEqual(len(names), 30)
            self.assertIn("readme_r.md", names)
            self.assertIn("rintro1.env", names)


if __name__ == "__main__":
    unittest.main()
