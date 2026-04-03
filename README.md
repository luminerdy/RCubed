# RCubed - Rubik's Cube Solving Robot

A Raspberry Pi-powered robot that solves Rubik's cubes using computer vision and the Kociemba algorithm.

## Hardware

- **Raspberry Pi 5** (16GB) with Hailo-8 AI accelerator
- **4 DS3218 servos** (270°) for gripper rotation
- **4 DS3218 servos** for rack-and-pinion grip/release
- **Pololu Maestro** servo controller
- **Camera** for cube scanning
- Based on [RCR3D design](https://rcr3d.com) by O.T. Vinta

## Project Structure

```
rcubed/
├── src/                    # Main application code
│   ├── scan_v7.py          # 6-face scanning sequence
│   ├── solve_cube.py       # Kociemba solver integration
│   ├── move_executor.py    # Translates moves to servo commands
│   ├── auto_solve.py       # Full scan→solve→execute pipeline
│   ├── collect_training_v2.py  # Training data collection
│   └── maestro.py          # Pololu Maestro servo library
├── scripts/                # Utilities and dev tools
│   ├── servo_calibrate.py  # Interactive calibration
│   ├── test_grippers.py    # Gripper testing
│   └── ...
├── config/                 # Configuration files
│   └── servo_config.json   # Servo calibration values
├── docs/                   # Documentation
│   ├── RULES.md            # Rotation rules and mechanics
│   ├── SCAN-SEQUENCE-FINAL.md
│   └── ...
├── cube_labeler/           # Flask web app for training data
├── training_scans/         # Training images (not in git)
└── tmp/                    # Temporary files (not in git)
```

## Progress

### Completed
- ✅ Hardware built and calibrated
- ✅ 6-face scanning sequence working
- ✅ Kociemba solver integrated
- ✅ First successful solves (2, 8, and 20-move solutions)
- ✅ Training data collection system
- ✅ Web labeler with validation

### In Progress
- 🔄 Training data collection and labeling
- 🔄 Custom YOLOv8 color detection model

### Planned
- ⏳ Hailo-8 deployment for fast inference
- ⏳ Full autonomous solving pipeline

## Servo Calibration

### Gripper Servos (channels 0, 2, 6, 8)
| Servo | A | B | C | D |
|-------|-----|------|------|------|
| 0 | 400 | 1100 | 1785 | 2420 |
| 2 | 400 | 1040 | 1710 | 2400 |
| 6 | 475 | 1120 | 1800 | 2425 |
| 8 | 450 | 1120 | 1810 | 2425 |

### Rack-and-Pinion Servos (channels 1, 3, 7, 9)
| Servo | Retracted | Hold |
|-------|-----------|------|
| 1 | 1890 | 1055 |
| 3 | 1815 | 1100 |
| 7 | 1875 | 990 |
| 9 | 1880 | 1100 |

## Face Centers
- F (Front) = White
- B (Back) = Yellow  
- R (Right) = Red
- L (Left) = Orange
- U (Up/Top) = Blue
- D (Down/Bottom) = Green

## License

MIT

## Author

Scotty (luminerdy)
