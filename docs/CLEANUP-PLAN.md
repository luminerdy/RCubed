# RCubed Code Cleanup Plan

## Current State Analysis

### src/ - Main Code
| File | Status | Notes |
|------|--------|-------|
| `cube_controller.py` | ✅ KEEP | New modular controller - THE standard going forward |
| `scan_v7.py` | ✅ KEEP | Working scanner, verified 2026-03-31 |
| `solve_cube.py` | ✅ KEEP | Kociemba integration |
| `maestro.py` | ✅ KEEP | Core servo library |
| `collect_training_v2.py` | ✅ KEEP | Training data collection |
| `auto_solve.py` | ⚠️ UPDATE | Uses old move_executor, needs to use cube_controller |
| `move_executor.py` | 🗑️ DELETE | Replaced by cube_controller |
| `move_executor_v2.py` | 🗑️ DELETE | Replaced by cube_controller |
| `full_solve.py` | 🗑️ DELETE | Redundant with auto_solve |

### scripts/ - Utilities
| File | Status | Notes |
|------|--------|-------|
| `calibrate_timing.py` | ✅ KEEP | New timing calibration |
| `servo_calibrate.py` | ✅ KEEP | Interactive calibration |
| `servo_visual_calibrate.py` | ⚠️ MAYBE | Visual calibration - check if useful |
| `camera_adjust.py` | ✅ KEEP | Camera setup |
| `camera_test.py` | ✅ KEEP | Camera testing |
| `retract_all.py` | ✅ KEEP | Safety reset |
| `set_neutral.py` | ✅ KEEP | Reset to neutral |
| `test_grippers.py` | ✅ KEEP | Gripper testing |
| `maestro_test.py` | ✅ KEEP | Basic servo test |

### scripts/ - DELETE (old/obsolete)
| File | Reason |
|------|--------|
| `scan_6faces.py` | Replaced by scan_v7.py |
| `scan_6faces_v2.py` | Replaced by scan_v7.py |
| `scan_6faces_v3.py` | Replaced by scan_v7.py |
| `scan_6faces_v4.py` | Replaced by scan_v7.py |
| `scan_6faces_v5.py` | Replaced by scan_v7.py |
| `scan_6faces_v6.py` | Replaced by scan_v7.py |
| `scan_6faces_noprompt.py` | Replaced by scan_v7.py |
| `fix_final.py` | One-off debug script |
| `fix_last.py` | One-off debug script |
| `fix_orientation.py` | One-off debug script |
| `fix_return.py` | One-off debug script |
| `fix_x180.py` | One-off debug script |
| `fix_y180.py` | One-off debug script |
| `test_calibrated_move.py` | Old test |
| `test_first_move.py` | Old test |
| `test_grippers_big.py` | Redundant with test_grippers.py |
| `test_rotations.py` | Can be replaced with cube_controller tests |
| `test_x_back.py` | Old debug script |
| `test_y_rotation.py` | Old debug script |
| `collect_training_data.py` | Replaced by collect_training_v2.py |
| `check_scans.py` | One-off utility |
| `label_images.py` | Replaced by cube_labeler app |
| `label_reviewer.py` | Replaced by cube_labeler app |
| `load_cube.py` | One-off script |
| `cube_color_test.py` | Old vision test |

### cube_labeler/ - Keep All
Flask app for labeling - all files needed.

## Cleanup Commands

```bash
# Delete old scan versions
rm scripts/scan_6faces*.py

# Delete fix scripts
rm scripts/fix_*.py

# Delete old tests
rm scripts/test_calibrated_move.py scripts/test_first_move.py
rm scripts/test_grippers_big.py scripts/test_rotations.py
rm scripts/test_x_back.py scripts/test_y_rotation.py

# Delete redundant scripts
rm scripts/collect_training_data.py scripts/check_scans.py
rm scripts/label_images.py scripts/label_reviewer.py
rm scripts/load_cube.py scripts/cube_color_test.py

# Delete old move executors
rm src/move_executor.py src/move_executor_v2.py src/full_solve.py
```

## Post-Cleanup Structure

```
rcubed/
├── src/
│   ├── cube_controller.py  # Main controller
│   ├── scan_v7.py          # Scanner
│   ├── solve_cube.py       # Kociemba solver
│   ├── auto_solve.py       # Full pipeline (needs update)
│   ├── collect_training_v2.py
│   └── maestro.py
├── scripts/
│   ├── calibrate_timing.py
│   ├── servo_calibrate.py
│   ├── camera_adjust.py
│   ├── camera_test.py
│   ├── retract_all.py
│   ├── set_neutral.py
│   ├── test_grippers.py
│   └── maestro_test.py
├── cube_labeler/
│   └── (all files)
├── config/
│   └── servo_config.json
└── docs/
    └── (all docs)
```

## Integration Tasks (after cleanup)

1. **Update auto_solve.py** to use CubeController instead of move_executor
2. **Add scan() method** to CubeController (or keep scan_v7.py separate)
3. **Create unified pipeline**: scan → detect colors → solve → execute
