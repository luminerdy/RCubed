# RCubed - Rubik's Cube Solving Robot

A Raspberry Pi-powered robot that solves Rubik's cubes using computer vision and the Kociemba algorithm.

## Hardware

- **Raspberry Pi 5** (16GB) with Hailo-8 AI accelerator
- **4 DS3218 servos** (270°) for gripper rotation
- **4 DS3218 servos** for rack-and-pinion grip/release
- **Pololu Maestro** servo controller
- **Camera** for cube scanning
- Based on [RCR3D design](https://rcr3d.com) by O.T. Vinta

## Software

- Python 3 with OpenCV for vision
- Kociemba algorithm for solving
- Custom YOLOv8 model (in progress) for color detection
- Flask web app for label review

## Project Structure

```
rcubed/
├── scan_v7.py           # 6-face scanning sequence
├── solve_cube.py        # Kociemba solver integration
├── move_executor.py     # Translates moves to servo commands
├── auto_solve.py        # Full scan→solve→execute pipeline
├── collect_training_v2.py  # Training data collection
├── cube_labeler/        # Web app for labeling training data
├── servo_config.json    # Servo calibration values
└── first_pass_labels.json  # Training labels
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
