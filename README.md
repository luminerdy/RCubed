# RCubed

A Rubik's cube solving robot: RCR3D mechanics (O.T. Vinta), eight DS3218 servos on a
Pololu Mini Maestro, a USB webcam, and a Raspberry Pi 5. Everything runs locally in
Python. No cloud, no LLM.

**Status (Sept 2026):** restarted from a clean base. The previous code is preserved under
[`legacy/`](legacy/) and at tag `v0-legacy`. See [docs/PLAN.md](docs/PLAN.md) for the
phases and [docs/HARDWARE.md](docs/HARDWARE.md) for the mechanics.

## Layout

```
rcubed/            the package
  config.py        loads config/robot.json (the only place calibration lives)
  maestro.py       Pololu serial protocol
  backends.py      MaestroBackend (real) / SimBackend (no hardware)
  robot.py         servo primitives, collision guard, persisted state
  choreography.py  face turns and whole-cube rotations
  cube_model.py    54-facelet cube model (tracking + tests)
  solver.py        Kociemba wrapper
  cli.py           python -m rcubed ...
config/robot.json  servo calibration, speeds, timing, camera crop
tests/             runs anywhere; the simulator stands in for the robot
legacy/            the pre-restart code and docs, for reference only
```

## Setup

On the Pi (or any machine, for simulation):

```bash
git clone https://github.com/luminerdy/RCubed rcubed && cd rcubed
pip3 install --break-system-packages -r requirements.txt
python3 -m pytest -q
```

The Maestro must be in *USB Dual Port* mode and your user in the `dialout` group. The
command port is found automatically via `/dev/serial/by-id`.

## Driving the robot

```bash
python3 -m rcubed status                  # remembered servo state
python3 -m rcubed safe-start              # from unknown state to all-B, released
python3 -m rcubed load                    # fingers clear; insert cube white front, blue top
python3 -m rcubed grip                    # engage all four grippers
python3 -m rcubed move "R U R' U'"        # standard notation; F/B handled automatically
python3 -m rcubed release
python3 -m rcubed retract                 # EMERGENCY: release everything, forget state
```

Add `--sim` to any command to run it against the simulator instead (prints a command
trace with `-v`, and the time the robot would have taken):

```bash
python3 -m rcubed --sim -v move "F2 B' L"
```

Ctrl-C during a move retracts all grippers and marks the state unknown, so the next
run starts with a safe startup.

## Hardware notes

- Grippers on channels 0 (L), 2 (U), 6 (R), 8 (D); their rack-and-pinion servos on 1, 3, 7, 9.
- Gripper positions A/B/C/D are 90° apart; B is neutral. From B: C = 90° CW, A = 90° CCW, D = 180°.
- There is no gripper on F or B. Those faces are turned by spinning the cube (y) so they reach R.
- A finger may sit at A or C only while both neighbouring fingers are at B or D. The
  `Robot` class enforces this and refuses moves that would violate it.

Calibration numbers live only in `config/robot.json`. Change them there, nowhere else.
