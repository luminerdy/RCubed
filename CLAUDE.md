# RCubed — Claude context

Rubik's cube solving robot: RCR3D mechanics, eight DS3218 servos on a Pololu Mini
Maestro, USB webcam, Raspberry Pi 5. Plain Python, runs entirely on the Pi. No cloud,
no LLM anywhere in the pipeline. Owner: Scotty (luminerdy).

**Restarted September 2026.** The new code is the `rcubed/` package. Everything under
`legacy/` (also tag `v0-legacy`) is the old code kept for reference only — do not extend
it, and do not port its bugs. `legacy/CLAUDE.md` describes that old world, not this one.

## Read these first

- `docs/PLAN.md` — phases, decisions made, and what is next. Keep its status current.
- `docs/HARDWARE.md` — mechanics, gripper geometry, the A/B/C/D positions.
- `docs/MOVES.md` — every token the `move` command accepts.
- `README.md` — layout and the CLI.

## Current status (update this line when it changes)

Phase 2 (robot layer) is code-complete and passes in the simulator. Next: hardware
acceptance on the Pi, steps 1–5 in `docs/PLAN.md` §2, starting with **no cube** in the
robot. Phase 3 (scanner) has not started. Open housekeeping: revoke the old GitHub token
and delete `~/github.txt` / `~/RootPW.txt` on the Pi.

## Where things run

- **Windows PC** (`projects\Claude\RCubed`): editing, tests, simulator. No hardware.
- **Pi 5** (`~/rcubed`, user `pi5rcube`): the only place `python3 -m rcubed` runs against
  real servos. Pull there; never edit there without committing.
- Git on the PC shows every `legacy/` file as modified — that is CRLF/LF line-ending
  noise (`git diff --ignore-cr-at-eol` is empty). Do not commit those, and do not
  "fix" it by rewriting the legacy files.

## Rules

1. **Tests before hardware.** `python3 -m pytest -q` must pass on any machine before code
   touches the robot. The simulator (`--sim`) stands in for the Maestro.
2. **Calibration lives only in `config/robot.json`.** Never hardcode pulse widths, speeds
   or timings in Python. `config/robot_state.json` is runtime state and is gitignored;
   the simulator must never write it.
3. **Collision guard is law.** A finger may be at A or C only while both neighbours are at
   B or D. `Robot` enforces this and refuses violating moves; never bypass it.
4. **Maestro port** comes from `maestro.find_port()` via `/dev/serial/by-id`. Never
   `ttyACM0`/`ttyACM1` literals.
5. **Physical-frame cube model.** `cube_model.py` tracks the cube as the robot holds it;
   expected sticker order for scans is read from the model, never hand-derived.
6. **No YOLO, no Hailo, no LLM.** Vision is per-patch colour classification with
   self-labelled data (see PLAN §4). Don't reintroduce the old approach.
7. Ctrl-C during a move must retract all grippers and mark state unknown. Keep it so.

## Commands

```bash
python3 -m pytest -q                         # anywhere
python3 -m rcubed --sim -v move "F R U R' U' F'"   # simulator with command trace
python3 -m rcubed status | safe-start | load | grip | release | retract   # on the Pi
python3 -m rcubed move "R U R' U'" [--no-home]
python3 -m rcubed servo 6 1500               # raw pulse width, calibration only
```

## Hardware quick reference

- Grippers: ch 0 (L), 2 (U), 6 (R), 8 (D). Rack-and-pinion: ch 1, 3, 7, 9.
- Positions A/B/C/D are 90° apart, B neutral. From B: C = 90° CW, A = 90° CCW, D = 180°.
- No gripper on F or B; those faces are turned by rotating the cube (y) to bring them to R.
- Standard load orientation: white front, blue top (orange L, red R, green D, yellow B).
- Maestro must be in USB Dual Port mode; user in `dialout`. If it goes unresponsive,
  power-cycle it.
- Lighting: a neutral-white diffuse ring light, not yet mounted. Required before any
  vision data is collected.
