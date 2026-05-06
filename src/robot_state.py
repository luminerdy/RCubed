#!/usr/bin/env python3
"""
Robot state persistence between script runs.

Tracks gripper positions and RP status so scripts within the same session
can skip safe startup. State is automatically invalid if written before
the last reboot — power-cycling the Pi always forces a fresh safe startup.

Usage:
    import robot_state

    state = robot_state.load()       # None if stale/dirty/missing
    robot_state.save(gripper_pos, rp_status)
    robot_state.invalidate()         # call from exception handlers
"""

import json
import time
from pathlib import Path

_STATE_FILE = Path(__file__).parent.parent / 'config' / 'robot_state.json'


def _boot_time() -> float:
    """Return Unix timestamp of last system boot."""
    with open('/proc/uptime') as f:
        return time.time() - float(f.read().split()[0])


def load() -> dict | None:
    """
    Load saved robot state.
    Returns state dict or None if state is missing, dirty, or from before last reboot.

    State dict keys:
        grippers: {servo_int: 'A'/'B'/'C'/'D'}
        rp:       {rp_int: 'retracted'/'hold'}
    """
    try:
        with open(_STATE_FILE) as f:
            raw = json.load(f)

        if not raw.get('clean', False):
            return None

        if raw.get('timestamp', 0) < _boot_time():
            return None  # written before last reboot — positions no longer valid

        return {
            'grippers': {int(k): v for k, v in raw['grippers'].items()},
            'rp':       {int(k): v for k, v in raw['rp'].items()},
        }

    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError):
        return None


def save(gripper_pos: dict, rp_status: dict):
    """Save current robot state as clean."""
    state = {
        'clean': True,
        'timestamp': time.time(),
        'grippers': {str(k): v for k, v in gripper_pos.items()},
        'rp':       {str(k): v for k, v in rp_status.items()},
    }
    with open(_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def invalidate():
    """Mark state as dirty. Call from exception handlers when operation was interrupted."""
    try:
        with open(_STATE_FILE) as f:
            state = json.load(f)
        state['clean'] = False
        with open(_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass  # if file is unreadable it's already effectively invalid
