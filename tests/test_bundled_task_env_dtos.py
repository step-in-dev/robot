"""Every bundled task file must contain at least one valid environment DTO."""


from __future__ import annotations

import json
import unittest
from pathlib import Path

import robot.loader as loader_module
from robot.loader import parse_task_payload
from robot.model import RobotEnvDto


def _bundled_tasks_dir() -> Path:
    return Path(loader_module.__file__).resolve().parent / "tasks"


class BundledTaskEnvDtosTest(unittest.TestCase):
    def test_all_bundled_task_env_dtos_are_valid(self) -> None:
        tasks_dir = _bundled_tasks_dir()
        self.assertTrue(tasks_dir.is_dir(), f"missing tasks dir: {tasks_dir}")

        for path in sorted(tasks_dir.glob("*.env")):
            with self.subTest(file=path.name):
                with path.open(encoding="utf-8") as stream:
                    data = json.load(stream)
                env_dtos, _ = parse_task_payload(data, path)
                self.assertTrue(
                    env_dtos,
                    f"{path.name}: envDtos must be a non-empty list of objects",
                )
                for index, raw in enumerate(env_dtos):
                    with self.subTest(file=path.name, index=index):
                        RobotEnvDto.from_dict(raw)


if __name__ == "__main__":
    unittest.main()
