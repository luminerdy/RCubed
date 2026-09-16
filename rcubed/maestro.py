"""Pololu Maestro serial driver (Pololu protocol, device number 12).

Only what the robot needs. Positions are in quarter-microseconds as the Maestro
expects; callers convert from microseconds (see backends.MaestroBackend).

The Maestro must be in "USB Dual Port" mode. It exposes two ttyACM ports; the
command port is the `-if00` entry under /dev/serial/by-id. The other one is the
TTL pass-through and silently ignores commands.
"""
from __future__ import annotations

import glob
import os

COMMAND_PORT_GLOB = "/dev/serial/by-id/usb-Pololu*Maestro*-if00"
DEFAULT_PORT = "/dev/ttyACM0"


def find_port() -> str:
    """Resolve the Maestro command port via its stable by-id symlink."""
    matches = sorted(glob.glob(COMMAND_PORT_GLOB))
    if matches:
        return os.path.realpath(matches[0])
    return DEFAULT_PORT


class Maestro:
    def __init__(self, port: str | None = None, device: int = 0x0C, timeout: float = 1.0):
        import serial  # lazy so the simulator works without pyserial

        self.port = port or find_port()
        self.device = device
        self.ser = serial.Serial(self.port, timeout=timeout)

    def close(self) -> None:
        self.ser.close()

    # ── protocol ────────────────────────────────────────────────────────
    def _send(self, *payload: int) -> None:
        self.ser.write(bytes([0xAA, self.device, *payload]))

    @staticmethod
    def _split(value: int) -> tuple[int, int]:
        return value & 0x7F, (value >> 7) & 0x7F

    def set_target(self, channel: int, quarter_us: int) -> None:
        lsb, msb = self._split(int(quarter_us))
        self._send(0x04, channel, lsb, msb)

    def set_speed(self, channel: int, speed: int) -> None:
        """0 = unlimited. Units: 0.25 us per 10 ms."""
        lsb, msb = self._split(int(speed))
        self._send(0x07, channel, lsb, msb)

    def set_accel(self, channel: int, accel: int) -> None:
        """0 = unlimited, 1 = slowest, 255 = fastest limited."""
        lsb, msb = self._split(int(accel))
        self._send(0x09, channel, lsb, msb)

    def get_position(self, channel: int) -> int:
        """Last commanded pulse width in quarter-us (not true servo feedback)."""
        self._send(0x10, channel)
        data = self.ser.read(2)
        if len(data) != 2:
            raise TimeoutError("Maestro did not answer get_position")
        return data[0] | (data[1] << 8)

    def get_moving_state(self) -> bool:
        """True while any channel with a speed/accel limit is still ramping."""
        self._send(0x13)
        data = self.ser.read(1)
        if len(data) != 1:
            raise TimeoutError("Maestro did not answer get_moving_state")
        return data[0] != 0

    def get_errors(self) -> int:
        """Read and clear the error register."""
        self._send(0x21)
        data = self.ser.read(2)
        if len(data) != 2:
            raise TimeoutError("Maestro did not answer get_errors")
        return data[0] | (data[1] << 8)

    def go_home(self) -> None:
        self._send(0x22)
