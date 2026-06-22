"""Build release zip archives for community task packs under community/."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence
import argparse
import sys
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# pylint: disable=wrong-import-position
from tools.markdown_front_matter import parse_markdown_front_matter
COMMUNITY_DIR = PROJECT_ROOT / "community"
PACK_DIR_GLOB = "pack*"
README_NAME = "readme.md"


@dataclass(frozen=True)
class CommunityPack:
    """One community task pack directory and its metadata."""

    directory: Path
    author: str
    prefix: str

    @property
    def zip_name(self) -> str:
        """Release archive file name for this pack."""
        return f"{self.prefix}tasks.zip"


def load_pack_metadata(pack_dir: Path) -> CommunityPack:
    """Load author and prefix from ``pack_dir/readme.md``."""
    readme_path = pack_dir / README_NAME
    if not readme_path.is_file():
        raise SystemExit(f"Missing {README_NAME} in {pack_dir}")
    front, _ = parse_markdown_front_matter(
        readme_path,
        source_label="Pack readme",
    )
    try:
        author = str(front["author"])
        prefix = str(front["prefix"])
    except KeyError as exc:
        raise SystemExit(
            f"Missing front matter field {exc.args[0]!r} in {readme_path}"
        ) from exc
    if not prefix.strip():
        raise SystemExit(f"prefix in {readme_path} must be a non-empty string")
    return CommunityPack(directory=pack_dir, author=author, prefix=prefix)


def discover_packs(community_dir: Path = COMMUNITY_DIR) -> List[CommunityPack]:
    """Return all packs under ``community_dir``, sorted by directory name."""
    if not community_dir.is_dir():
        return []
    packs: List[CommunityPack] = []
    seen_prefixes: dict[str, Path] = {}
    for pack_dir in sorted(community_dir.glob(PACK_DIR_GLOB)):
        if not pack_dir.is_dir():
            continue
        pack = load_pack_metadata(pack_dir)
        if pack.prefix in seen_prefixes:
            other = seen_prefixes[pack.prefix]
            raise SystemExit(
                f"Duplicate pack prefix {pack.prefix!r} in {pack_dir} "
                f"and {other}"
            )
        seen_prefixes[pack.prefix] = pack_dir
        packs.append(pack)
    return packs


def pack_root_files(pack_dir: Path) -> List[Path]:
    """Return regular files directly in ``pack_dir`` (no subdirectories)."""
    return sorted(
        path
        for path in pack_dir.iterdir()
        if path.is_file()
    )


def readme_archive_name(prefix: str) -> str:
    """Return the readme file name inside a release zip."""
    return f"readme_{prefix}.md"


def zip_arcname(file_path: Path, pack: CommunityPack) -> str:
    """Return the archive entry name for one pack file."""
    if file_path.name == README_NAME:
        return readme_archive_name(pack.prefix)
    return file_path.name


def build_pack_zip(pack: CommunityPack, output_dir: Path) -> Path:
    """Zip flat files from one pack into ``{prefix}tasks.zip``."""
    files = pack_root_files(pack.directory)
    if not files:
        raise SystemExit(f"No files to zip in {pack.directory}")
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / pack.zip_name
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in files:
            archive.write(file_path, arcname=zip_arcname(file_path, pack))
    return zip_path


def build_all_community_packs(
    output_dir: Path,
    *,
    community_dir: Path = COMMUNITY_DIR,
) -> List[Path]:
    """Build release zips for every pack under ``community_dir``."""
    packs = discover_packs(community_dir)
    return [build_pack_zip(pack, output_dir) for pack in packs]


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT,
        help="Directory for generated zip files (default: repository root)",
    )
    parser.add_argument(
        "--community-dir",
        type=Path,
        default=COMMUNITY_DIR,
        help="Community packs root (default: community/)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    paths = build_all_community_packs(
        args.output_dir.resolve(),
        community_dir=args.community_dir.resolve(),
    )
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
