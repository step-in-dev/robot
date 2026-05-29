"""Shared helpers for model unit tests."""

from robot.model import RobotEnv, RobotEnvDto


def make_env(data):
    return RobotEnv(RobotEnvDto.from_dict(data))
