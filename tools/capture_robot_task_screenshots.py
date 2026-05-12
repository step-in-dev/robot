from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from robot.i18n import SUPPORTED_LANGUAGES


def _require_command(cmd: str) -> None:
    if subprocess.run(
        ["bash", "-lc", f"command -v {cmd}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode != 0:
        raise RuntimeError(f"Required command not found: {cmd}")


def _all_window_ids() -> set[str]:
    proc = subprocess.run(
        ["wmctrl", "-l"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return set()

    ids: set[str] = set()
    for line in proc.stdout.splitlines():
        parts = line.split(None, 1)
        if not parts:
            continue
        ids.add(parts[0])
    return ids


def _find_new_window_id(
    *,
    before_ids: set[str],
    proc: subprocess.Popen[bytes],
    timeout_seconds: float = 10.0,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        current_ids = _all_window_ids()
        new_ids = current_ids - before_ids
        if new_ids:
            return min(new_ids)
        if proc.poll() is not None:
            raise RuntimeError(
                f"Robot process exited before opening window (code={proc.returncode})"
            )
        time.sleep(0.1)
    raise TimeoutError("Robot window was not found")


def _stop_process(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=2.0)
        return
    except subprocess.TimeoutExpired:
        pass
    proc.send_signal(signal.SIGKILL)
    proc.wait(timeout=2.0)


def capture_for_language(
    *,
    python_executable: str,
    task_id: str,
    language: str,
    output_path: Path,
    workdir: Path,
) -> None:
    script_body = textwrap.dedent(
        f"""
        from robot import *

        task({task_id!r})
        """
    )

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".py",
        prefix="tmp_robot_task_",
        delete=False,
        dir=workdir,
    ) as f:
        f.write(script_body)
        script_path = Path(f.name)

    env = os.environ.copy()
    env["ROBOT_LANGUAGE"] = language
    env["PYTHONUNBUFFERED"] = "1"

    proc: subprocess.Popen[bytes] | None = None
    try:
        before_ids = _all_window_ids()
        proc = subprocess.Popen(
            [python_executable, str(script_path)],
            cwd=str(workdir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        window_id = _find_new_window_id(
            before_ids=before_ids, proc=proc, timeout_seconds=12.0
        )
        subprocess.run(["wmctrl", "-ia", window_id], check=True)
        time.sleep(0.25)
        subprocess.run(
            ["gnome-screenshot", "-w", "-f", str(output_path)],
            check=True,
        )
    finally:
        if proc is not None:
            _stop_process(proc)
        script_path.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run robot task for each supported language and save "
            "window screenshots (with OS title bar)."
        )
    )
    parser.add_argument(
        "--task",
        default="fun17",
        help="Task id for task('<id>'). Default: fun17",
    )
    parser.add_argument(
        "--output-dir",
        default="screenshots_by_language",
        help="Directory where PNG files are written.",
    )
    parser.add_argument(
        "--languages",
        nargs="*",
        default=list(SUPPORTED_LANGUAGES),
        help=(
            "Optional language codes. If omitted, uses all supported languages "
            "from robot.i18n.SUPPORTED_LANGUAGES."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    _require_command("wmctrl")
    _require_command("gnome-screenshot")

    workdir = PROJECT_ROOT
    output_dir = (workdir / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    failed: list[tuple[str, str]] = []
    for language in args.languages:
        output_path = output_dir / f"{args.task}_{language}.png"
        print(f"[{language}] capturing -> {output_path}")
        try:
            capture_for_language(
                python_executable=sys.executable,
                task_id=args.task,
                language=language,
                output_path=output_path,
                workdir=workdir,
            )
        except Exception as exc:  # noqa: BLE001
            failed.append((language, str(exc)))
            print(f"[{language}] FAILED: {exc}")
        else:
            print(f"[{language}] OK")

    if failed:
        print("\nSome languages failed:")
        for lang, reason in failed:
            print(f" - {lang}: {reason}")
        return 1

    print("\nAll screenshots captured successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
