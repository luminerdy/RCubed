# RCubed - Claude Context

## What This Is
A Raspberry Pi 5 robot that physically solves a Rubik's cube. Uses DS3218 servos controlled by a Pololu Maestro, and the Kociemba algorithm for solutions. Built by Scotty (luminerdy).

## This Pi
- **User:** pi5rcube
- **Code:** `~/rcubed/` (this directory) — cloned from https://github.com/luminerdy/RCubed
- **GitHub creds:** `~/github.txt` (token + login)
- **RubikPi agent workspace:** `/home/pi5rcube/RCubed/` (identity, memory, project docs)

## Hardware
- Pololu Maestro servo controller → `/dev/ttyACM0` (may be ttyACM1 after USB replug)
- Maestro uses quarter-microseconds (multiply μs × 4)
- 8× DS3218 servos: grippers 0,2,6,8 (rotate faces) + RP servos 1,3,7,9 (grip/retract)
- USB camera, front-facing
- Blue LED lighting (causes W/Y color confusion — manual verification needed)

## Setup Status (2026-05-05)
- ✅ dialout group: already set
- ✅ Repo cloned to ~/rcubed
- ✅ Dependencies installed: pyserial, opencv-python, kociemba, anthropic, flask, numpy
- ⚠️ Maestro: not yet connected/tested on this reflashed Pi
- ⚠️ ANTHROPIC_API_KEY: needs to be set in ~/.bashrc
- ⚠️ Camera white balance: run after each camera reconnect

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
1. Plug in Maestro → test with `scripts/retract_all.py`
2. Set ANTHROPIC_API_KEY in ~/.bashrc
3. Run `scripts/calibrate_timing.py` to optimize servo speeds
4. Collect more training scans (at 8/100+ needed for local YOLOv8 model)
5. Update auto_solve.py to use CubeController
6. Build unified Pipeline class (scan → solve → execute)
