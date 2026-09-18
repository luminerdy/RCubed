"""Scan illumination.

The scanner asks for a named lighting state before each photo and turns the lights
off afterwards. With no controllable light fitted, NullLights does nothing and the
single state "default" means "whatever light is on the rig".

An addressable ring (NeoPixel) backend can be added here later with states such as
"white", "red", "green", "blue", "left-half", "right-half".
"""
from __future__ import annotations

from typing import Protocol


class Lights(Protocol):
    def set(self, state: str) -> None: ...
    def off(self) -> None: ...
    def close(self) -> None: ...


class NullLights:
    def set(self, state: str) -> None:
        pass

    def off(self) -> None:
        pass

    def close(self) -> None:
        pass
