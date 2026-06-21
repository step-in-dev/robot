"""Tests for batch task-id selection in capture_all_task_screenshots."""

from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from robot.task_catalog import TaskCatalog
from tests.loader_runtime._helpers import write_minimal_task_env
from tools.capture_all_task_screenshots import resolve_task_ids, validate_capture_args
from tools.site_catalog import discover_site_catalog


def _write_pack(
    community_dir: Path,
    pack_name: str,
    *,
    prefix: str,
    task_ids: tuple[str, ...],
) -> Path:
    """Create a temporary community pack with minimal valid task files."""
    pack_dir = community_dir / pack_name
    pack_dir.mkdir(parents=True)
    (pack_dir / "readme.md").write_text(
        "---\n"
        'author: "Test Author"\n'
        f'prefix: "{prefix}"\n'
        "---\n",
        encoding="utf-8",
    )
    for task_id in task_ids:
        write_minimal_task_env(pack_dir / f"{task_id}.env", task_id)
    return pack_dir


def _args(**overrides) -> argparse.Namespace:
    """Return Namespace matching capture_all_task_screenshots.parse_args()."""
    base = {
        "task": None,
        "theme": None,
        "settle_seconds": 0.85,
        "skip_existing": False,
        "dry_run": False,
        "community_only": False,
        "pack_prefix": None,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


class ResolveTaskIdsTest(unittest.TestCase):
    def test_defaults_to_bundled_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundled_dir = Path(temp_dir) / "bundled"
            bundled_dir.mkdir()
            write_minimal_task_env(bundled_dir / "intro1.env", "intro1")
            write_minimal_task_env(bundled_dir / "if2.env", "if2")
            community_dir = Path(temp_dir) / "community"
            _write_pack(community_dir, "pack1", prefix="r", task_ids=("rintro1",))

            site_catalog = discover_site_catalog(
                bundled_catalog=TaskCatalog.discover(bundled_dir),
                community_dir=community_dir,
            )

            task_ids = resolve_task_ids(site_catalog, _args())

        self.assertEqual(task_ids, ["intro1", "if2"])

    def test_community_only_uses_pack_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundled_dir = Path(temp_dir) / "bundled"
            bundled_dir.mkdir()
            write_minimal_task_env(bundled_dir / "intro1.env", "intro1")
            community_dir = Path(temp_dir) / "community"
            _write_pack(
                community_dir,
                "pack1",
                prefix="r",
                task_ids=("rintro2", "rintro1", "rfun1"),
            )

            site_catalog = discover_site_catalog(
                bundled_catalog=TaskCatalog.discover(bundled_dir),
                community_dir=community_dir,
            )

            task_ids = resolve_task_ids(site_catalog, _args(community_only=True))

        self.assertEqual(task_ids, ["rintro1", "rintro2", "rfun1"])

    def test_pack_prefix_filters_community_packs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundled_dir = Path(temp_dir) / "bundled"
            bundled_dir.mkdir()
            write_minimal_task_env(bundled_dir / "intro1.env", "intro1")
            community_dir = Path(temp_dir) / "community"
            _write_pack(community_dir, "pack1", prefix="r", task_ids=("rintro1",))
            _write_pack(community_dir, "pack2", prefix="s", task_ids=("sintro1",))

            site_catalog = discover_site_catalog(
                bundled_catalog=TaskCatalog.discover(bundled_dir),
                community_dir=community_dir,
            )

            task_ids = resolve_task_ids(
                site_catalog,
                _args(community_only=True, pack_prefix=["s"]),
            )

        self.assertEqual(task_ids, ["sintro1"])

    def test_pack_prefix_requires_community_only(self) -> None:
        with self.assertRaises(ValueError):
            validate_capture_args(_args(pack_prefix=["r"]))


if __name__ == "__main__":
    unittest.main()
