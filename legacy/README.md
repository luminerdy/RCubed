# RCubed - Rubik's Cube Solving Robot

A Raspberry Pi-powered robot that solves Rubik's cubes using computer vision and the Kociemba algorithm.

## Hardware

- **Raspberry Pi 5** (16GB) with Hailo-8 AI accelerator
- **4 DS3218 servos** (270°) for gripper rotation
- **4 DS3218 servos** for rack-and-pinion grip/release
- **Pololu Maestro** servo controller
- **Camera** for cube scanning
- Based on [RCR3D design](https://rcr3d.com) by O.T. Vinta

## Quick Start

```bash
# Test gripper movements
python3 scripts/test_grippers.py

# Run timing calibration
python3 scripts/calibrate_timing.py

# Execute a solution
python3 src/cube_controller.py "R U R' F2"

# Scan cube faces
python3 src/scan_v7.py
```

## Project Structure

```
rcubed/
├── src/                    # Main application code
│   ├── cube_controller.py  # Robot control (standard cube notation)
│   ├── scan_v7.py          # 6-face scanning sequence
│   ├── solve_cube.py       # Kociemba solver integration
│   ├── auto_solve.py       # Full pipeline (needs update)
│   ├── collect_training_v2.py
│   └── maestro.py          # Servo library
├── scripts/                # Utilities
│   ├── calibrate_timing.py # Measure actual servo times
│   ├── servo_calibrate.py  # Interactive calibration
│   ├── camera_adjust.py    # Camera setup
│   ├── test_grippers.py    # Gripper testing
│   ├── retract_all.py      # Safety reset
│   └── set_neutral.py      # Reset servos
├── cube_labeler/           # Flask app for labeling training data
├── config/                 # servo_config.json
├── docs/                   # Documentation
│   ├── CUBE-CONTROLLER.md  # Controller API
│   ├── RULES.md            # Rotation mechanics
│   ├── BRAINSTORM.md       # Project roadmap
│   └── ...
└── training_scans/         # Training images (not in git)
```

## Cube Controller

Standard cube notation with automatic F/B handling:

```python
from cube_controller import CubeController

with CubeController() as cube:
    cube.R()              # Right CW
    cube.Rp()             # Right CCW (prime)
    cube.R2()             # Right 180°
    cube.F()              # Front (auto-rotates cube)
    cube.execute("R U R' F2")  # Full solution
```

See [docs/CUBE-CONTROLLER.md](docs/CUBE-CONTROLLER.md) for full API.

## Progress

### Completed ✅
- Hardware built and calibrated
- 6-face scanning sequence (scan_v7.py)
- Kociemba solver integrated
- Modular controller with standard notation
- Successful solves (2, 8, and 20-move solutions)
- Training data collection system
- Web labeler with validation

### In Progress 🔄
- Timing calibration for speed optimization
- Training data collection (8 scans, need 100+)
- YOLOv8 color detection model

### Planned ⏳
- Hailo-8 deployment
- Full autonomous pipeline
- Error recovery

## Servo Calibration

### Gripper Servos (0, 2, 6, 8)
| Servo | A | B | C | D |
|-------|-----|------|------|------|
| 0 | 400 | 1100 | 1785 | 2420 |
| 2 | 400 | 1040 | 1710 | 2400 |
| 6 | 475 | 1120 | 1800 | 2425 |
| 8 | 450 | 1120 | 1810 | 2425 |

### RP Servos (1, 3, 7, 9)
| Servo | Retracted | Hold |
|-------|-----------|------|
| 1 | 1890 | 1055 |
| 3 | 1815 | 1100 |
| 7 | 1875 | 990 |
| 9 | 1880 | 1100 |

## Standard Cube Orientation

```
        Blue (U)
           ↑
Orange (L) ← White (F) → Red (R)
           ↓
        Green (D)
        
    Yellow (B) = behind
```

## License

MIT

## Author

Scotty (luminerdy)
