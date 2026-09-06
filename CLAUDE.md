# RCubed - Claude Context

## What This Is
A Raspberry Pi 5 robot that physically solves a Rubik's cube. Uses DS3218 servos controlled by a Pololu Maestro, and the Kociemba algorithm for solutions. Built by Scotty (luminerdy).

## This Pi
- **User:** pi5rcube
- **Code:** `~/rcubed/` (this directory) — cloned from https://github.com/luminerdy/RCubed
- **GitHub creds:** `~/github.txt` (token + login)
- **RubikPi agent workspace:** `/home/pi5rcube/RCubed/` (identity, memory, project docs)

## Hardware
- Pololu Maestro servo controller — port resolved by `maestro.find_port()` via
  `/dev/serial/by-id/usb-Pololu*-if00` (the command port). Never hardcode
  `ttyACM1`; that's the TTL port and commands there go nowhere.
- Maestro uses quarter-microseconds (multiply μs × 4)
- 8× DS3218 servos: grippers 0,2,6,8 (rotate faces) + RP servos 1,3,7,9 (grip/retract)
- USB camera, front-facing
- Blue LED lighting (causes W/Y color confusion — manual verification needed)

## Setup Status (2026-09-05)
- ✅ dialout group: already set
- ✅ Repo cloned to ~/rcubed
- ✅ Dependencies installed (see requirements.txt) — all six import cleanly
- ✅ Maestro detected on USB (Mini Maestro 12-Channel, serial 00490905)
- ✅ USB webcam detected (SunplusIT 4bcf:4c10) on /dev/video0
- ⚠️ ANTHROPIC_API_KEY: still not set in ~/.bashrc — auto_solve.py can't run
- ⚠️ Nothing has been run on hardware since the reflash (no config/robot_state.json)
- ⚠️ Camera white balance: run after each camera reconnect
- ❌ training_scans/ absent — labels are in git, images are not

## Key Commands
```bash
python3 scripts/retract_all.py          # safety reset — run first
python3 scripts/test_grippers.py        # verify all 8 servos move
python3 src/scan_v7.py                  # scan 6 cube faces
python3 src/cube_controller.py "R U R'" # execute moves
python3 src/auto_solve.py               # full autonomous pipeline (needs API key)
```

## Servo Calibration (verified 2026-04-03)
### Gripper servos — face turn CW=B→C, CCW=B→A, 180°=B→D
| Servo | Face | A    | B    | C    | D    |
|-------|------|------|------|------|------|
| 0     | Left | 400  | 1100 | 1785 | 2420 |
| 2     | Up   | 400  | 1040 | 1710 | 2400 |
| 6     | Right| 475  | 1120 | 1800 | 2425 |
| 8     | Down | 450  | 1120 | 1810 | 2425 |

### RP servos
| Servo | Side  | Retracted | Hold |
|-------|-------|-----------|------|
| 1     | Left  | 1890      | 1055 |
| 3     | Up    | 1815      | 1100 |
| 7     | Right | 1875      | 990  |
| 9     | Down  | 1880      | 1100 |

## Movement Rules
- y rotation (right→front): 2:B→C, 8:B→A
- y' rotation (left→front): 2:B→A, 8:B→C
- x rotation (top→front): 0:B→C, 6:B→A
- X rotation speeds: servo 0=60, servo 6=45
- F/B moves: auto-handled by CubeController via y/y' rotation + R gripper

## Standard Cube Orientation
```
        Blue (U)
           ↑
Orange (L) ← White (F) → Red (R)
           ↓
        Green (D)      Yellow (B) = behind
```

## Known Issues
- Maestro occasionally goes unresponsive → reboot Pi or power-cycle Maestro
- `docs/CUBE-CONTROLLER.md` has a doc error: y/y' physical action columns are swapped in the table — the actual code is correct
- `src/auto_solve.py` needs update to use CubeController (currently uses old move_executor logic)

## What's Next
See `docs/ACTION-PLAN.md` — Phase 0 (validate on hardware) is the current blocker.
1. `scripts/retract_all.py` → `scripts/test_grippers.py`, confirm robot_state.json appears
2. Set ANTHROPIC_API_KEY in ~/.bashrc
3. Run `scripts/calibrate_timing.py` to optimize servo speeds
4. Restore or re-collect training scans (images are not in git)
5. Update auto_solve.py to use CubeController — it still shells out to the
   deleted `move_executor.py`, so it is currently broken
6. Build unified Pipeline class (scan → solve → execute)
