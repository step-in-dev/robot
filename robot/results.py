"""Run outcome types and final-state checking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .model import RobotEnv

RunStatus = Literal["success", "wrong", "crashed", "error"]


@dataclass(frozen=True)
class RunResult:
    status: RunStatus
    message: str
    details: str = ""

    @property
    def success(self) -> bool:
        """Return whether the run finished with status ``success``."""
        return self.status == "success"


def check_final_state(env: RobotEnv) -> RunResult:
    """Map environment final-state check to a ``RunResult``."""
    if env.is_in_final_state():
        return RunResult(status="success", message="")
    return RunResult(status="wrong", message="")
