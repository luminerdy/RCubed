"""Hardware backends: the real Maestro, and a simulator for development off-robot.

Both speak the same tiny interface, in microseconds:

    set_target(channel, us)   set_speed(channel, speed)   set_accel(channel, accel)
    moving() -> bool | None   sleep(seconds)              close()
"""
from __future__ import annotations

import time
from typing import Protocol


class Backend(Protocol):
    def set_target(self, channel: int, us: int) -> None: ...
    def set_speed(self, channel: int, speed: int) -> None: ...
    def set_accel(self, channel: int, accel: int) -> None: ...
    def moving(self) -> bool | None: ...
    def sleep(self, seconds: float) -> None: ...
    def close(self) -> None: ...


class MaestroBackend:
    def __init__(self, port: str | None = None):
        from .maestro import Maestro

        self.m = Maestro(port)
        self.port = self.m.port

    def set_target(self, channel: int, us: int) -> None:
        self.m.set_target(channel, us * 4)

    def set_speed(self, channel: int, speed: int) -> None:
        self.m.set_speed(channel, speed)

    def set_accel(self, channel: int, accel: int) -> None:
        self.m.set_accel(channel, accel)

    def moving(self) -> bool | None:
        try:
            return self.m.get_moving_state()
        except Exception:
            return None

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def close(self) -> None:
        self.m.close()


class SimBackend:
    """Records every command. `realtime=True` also sleeps for real, so a dry run
    takes as long as the robot would; otherwise time is only accumulated."""

    def __init__(self, realtime: bool = False, echo: bool = False):
        self.realtime = realtime
        self.echo = echo
        self.targets: dict[int, int] = {}
        self.speeds: dict[int, int] = {}
        self.accels: dict[int, int] = {}
        self.log: list[tuple] = []
        self.clock = 0.0

    def _rec(self, *entry) -> None:
        self.log.append(entry)
        if self.echo:
            print(f"  [sim t={self.clock:6.1f}s] " + " ".join(str(e) for e in entry))

    def set_target(self, channel: int, us: int) -> None:
        self.targets[channel] = us
        self._rec("target", channel, us)

    def set_speed(self, channel: int, speed: int) -> None:
        self.speeds[channel] = speed
        self._rec("speed", channel, speed)

    def set_accel(self, channel: int, accel: int) -> None:
        self.accels[channel] = accel
        self._rec("accel", channel, accel)

    def moving(self) -> bool | None:
        return False

    def sleep(self, seconds: float) -> None:
        self.clock += seconds
        self._rec("sleep", round(seconds, 2))
        if self.realtime:
            time.sleep(seconds)

    def close(self) -> None:
        self._rec("close")
