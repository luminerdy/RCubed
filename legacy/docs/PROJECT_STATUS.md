# RCubed Project Status
**Last Updated: 2026-02-15**

## What Is RCubed?
A fully autonomous Rubik's Cube solving robot built on a Raspberry Pi 5 ("RubiksPi"), replacing the original closed-source Windows UWP app from the OTVINTA RCR3D design (rcr3d.com). The robot uses 4 gripper arms with DS3218 servos on a rack-and-pinion system, controlled via a Pololu Maestro servo controller.

## Hardware
- **Brain:** Raspberry Pi 5, 16GB, Hailo-8 AI hat V1 (with desktop GUI)
- **Gripper Servos:** 4× DS3218 (270°) — rotate to grip/turn cube faces
- **Rack-and-Pinion Servos:** 4× HS-311 (180°) — approach/retract grippers toward cube
- **Controller:** Pololu Mini Maestro 12-Channel USB Servo Controller (`/dev/ttyACM0`)
- **Camera:** USB webcam, front-facing, mounted on adjustable camera holder between grippers
- **Lighting:** White LEDs (replaced original blue LEDs that ruined color detection)
- **Power:** 6V 3A wall charger via DC balun adapter to Maestro power pins
- **Grip Aids:** Hair rubber bands on gripper fingers (increases friction, reduces cube slipping)

## What's Working ✅

### Scan Choreography (`full_solve.py`)
- All 6 faces scanned cleanly in sequence
- Grippers 2 & 8 start at C & A to keep fingers out of camera view
- Cube returns to original orientation after scanning
- Safety enforced: always ≥ 2 grippers holding, engage before retract

### Color Detection (Vision API)
- Cropped face images sent to Claude Sonnet API for color reading
- Correctly identifies all 6 colors (R, O, Y, G, B, W)
- Auto-correction logic for common O↔R misreads
- OpenCV approaches (HSV, k-means) all failed under current lighting — vision model is the working solution

### Kociemba Solver
- Builds valid 54-character cube string from face readings
- Rotation corrections applied per face (U=90°CW, D=90°CCW, others=none)
- Validates color counts and unique centers before solving
- Produces optimal solutions (typically 19-21 moves)

### Move Executor (`move_executor.py`)
- Translates Kociemba notation (R, R', R2, U, F, B, etc.) to servo choreography
- Direct face turns: U, D, L, R via their respective grippers
- F/B moves via cube rotation: F = y_CW → R turn → y_CCW
- Simultaneous RP engagement for stability
- Successfully executed 12/19 moves in best run

### Autonomous Solver (`auto_solve.py`)
- Single-command full pipeline: scan → vision API read → Kociemba solve → execute
- Options: `--dry-run`, `--scan-only`, `--no-scan`
- Auto-detects Maestro port (ttyACM0/ttyACM1)
- Reads API key from environment or OpenClaw auth store
- **Note:** API key needs to be set up (current OpenClaw auth key returned 401)

## What's Not Working Yet ❌

### Gripper Mechanical Issues
- **Gripper fingers catch cube layer edges** during rack-and-pinion engagement
- Small layer shifts accumulate over multiple moves
- Eventually causes turns to bind, servos to stall, USB I/O errors
- **Cube slips downward** over repeated moves due to gravity + grip loosening
- Rubber bands added to gripper fingers (per OTVINTA recommendation) — may need more

### Result
- Best run: 12 out of 19 moves completed before stall
- Root cause is mechanical, not software

## Design Reference (OTVINTA RCR3D — rcr3d.com)
- Original design by O.T. Vinta, fully 3D-printed (~59 hours print time, ~867g filament)
- 14 unique printed parts: arms, sliders, pinions, racks, corners, grippers, legs, camera holder, etc.
- 4 arms, each with DS3218 (gripper rotate) + HS-311 (rack-and-pinion approach/retract)
- Even Maestro channels = gripper servos, odd = rack-and-pinion, channels 4 & 5 skipped
- Original software: Windows UWP app (paid license, closed source) — NOT what we use
- We're building our own Python-based solution on Pi 5 with OpenCV + Kociemba
- **Key tip from site:** Hair rubber bands on grippers "dramatically reduces the chance of the cube being accidentally dragged sideways by a retracting gripper"
- **Recommended cube:** Standard stickerless, smooth-operation (NOT a speed cube)
- Gripper acceleration set to 110 in Maestro for all gripper servos
- Camera holder is adjustable via 4 rod clamps connecting to main frame

## Key Files
| File | Purpose |
|------|---------|
| `~/rcubed/auto_solve.py` | Full autonomous pipeline |
| `~/rcubed/full_solve.py` | Scan choreography + return to solve position |
| `~/rcubed/move_executor.py` | Kociemba moves → servo commands |
| `~/rcubed/solve_cube.py` | OpenCV color detection (not reliable yet) |
| `~/rcubed/maestro.py` | Maestro servo controller library |
| `~/rcubed/servo_config.json` | Servo calibration values |
| `~/rcubed/scans/` | Face images from last scan |

## Servo Calibration (Current)

### Gripper Servos (4 positions each, ~90° apart)
| Servo | Arm | A | B | C | D |
|-------|-----|---|---|---|---|
| 0 | Left | 467 | 1150 | 1806 | 2500 |
| 2 | Top/Back | 432 | 1064 | 1761 | 2415 |
| 6 | Right | 440 | 1075 | 1761 | 2393 |
| 8 | Bottom | 442 | 1118 | 1771 | 2436 |

### Rack-and-Pinion Servos (2 positions each)
| Servo | Arm | Retracted | Hold |
|-------|-----|-----------|------|
| 1 | Left | 1857 | 1090 |
| 3 | Top/Back | 1758 | 1050 |
| 7 | Right | 1692 | 776 |
| 9 | Bottom | 1856 | 1008 |

*All values in microseconds (μs). Maestro library uses quarter-μs (multiply × 4).*

## Mechanics Reference
- **Gripper direction:** A→B→C→D = counter-clockwise from cube's perspective
- **Face turns:** CW = B→A, CCW = B→C, 180° = B→D
- **Cube rotation:** Opposing grippers (2&8 or 0&6) move in opposite servo directions
- **Rotation clearance:** Adjacent RP servos must be retracted during whole-cube rotation
- **Scan start position:** 0:B, 2:C, 6:B, 8:A, RP 3&9 hold, RP 1&7 retracted
- **Solve start position:** All grippers at B, all RP holding

## Next Steps

### Immediate (Hardware)
1. **Add more rubber bands to grippers** — increase friction to prevent cube slipping
2. **Adjust gripper finger design** — taper/chamfer tips so they slide over layer edges instead of catching
3. **Re-calibrate RP hold positions** — tighter grip to prevent cube slipping down
4. **Re-calibrate gripper positions** — Scotty adjusting A/B/C/D values

### After Hardware Fix
5. **Test full solve end-to-end** — scan through execution with no stalls
6. **Set up Anthropic API key** — for `auto_solve.py` autonomous operation
7. **Verify and celebrate** 🎲

### Future Improvements
8. **Improve OpenCV color detection** — eliminate vision API dependency for fully offline solves
9. **Optimize timing** — reduce delays for faster solves
10. **Error recovery** — detect USB errors and retry/resume mid-solve
11. **Hailo-8 integration** — use AI accelerator for on-device vision inference
