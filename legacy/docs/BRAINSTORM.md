# RCubed Brainstorm - What We Have, Need, and Missing

## What We Have ✅

### Hardware
- 4 gripper servos (DS3218, 270°) - calibrated
- 4 rack-and-pinion servos (DS3218) - calibrated
- Pololu Maestro controller
- Pi Camera
- Pi 5 with Hailo-8 AI accelerator
- Foam tape grippers (working well)
- Stable power (fixed Maestro crashes)

### Software - Core
| Component | File | Status |
|-----------|------|--------|
| Robot Controller | `cube_controller.py` | ✅ New, untested |
| Scanner | `scan_v7.py` | ✅ Working, verified 3/31 |
| Solver | `solve_cube.py` | ✅ Kociemba working |
| Servo Library | `maestro.py` | ✅ Working |
| Full Pipeline | `auto_solve.py` | ⚠️ Needs update to use cube_controller |

### Software - Training
| Component | File | Status |
|-----------|------|--------|
| Data Collection | `collect_training_v2.py` | ✅ Working |
| Labeling App | `cube_labeler/` | ✅ Working |
| Training Data | `training_scans/` | 8 good scans |

### Software - Utilities
| Component | File | Status |
|-----------|------|--------|
| Timing Calibration | `calibrate_timing.py` | ✅ New, untested |
| Servo Calibration | `servo_calibrate.py` | ✅ Working |
| Camera Setup | `camera_adjust.py` | ✅ Working |

## What We Need To Do 📋

### Immediate (Test Day)
1. **Run timing calibration** - Get optimized TIMING values
2. **Test cube_controller.py** - Verify moves work correctly
3. **Verify rotation directions** - Especially y/y' and F/B handling

### Short Term (This Week)
1. **Update auto_solve.py** - Use CubeController instead of old move_executor
2. **Collect more training data** - Target: 100+ scans
3. **Train YOLOv8 model** - Replace API-based color detection
4. **Integrate scanner with controller** - Unified workflow

### Medium Term
1. **End-to-end autonomous solve** - No human intervention
2. **Speed optimization** - After timing calibration
3. **Error recovery** - Handle drops, stalls, misreads

## What's Missing ❓

### Critical Gaps
1. **Vision model** - Still using Anthropic API for color detection (slow, expensive)
   - Need: Trained YOLOv8 on Hailo-8
   - Have: 8 scans (need 100+)
   
2. **Unified pipeline** - Components exist but not integrated
   - scan_v7.py (scanning)
   - cube_controller.py (moves)
   - solve_cube.py (solving)
   - Need: One script that does scan→solve→execute

3. **Error handling** - What happens when:
   - Cube drops mid-solve?
   - Servo stalls?
   - Color misread?
   - Camera blocked?

### Nice to Have
1. **Z rotations** - Not implemented (rarely needed)
2. **Speed display** - Show solve time, move count
3. **Web interface** - Control robot from phone/laptop
4. **Scramble generator** - Auto-scramble for testing

## Architecture Decision: Integration

### Option A: Monolithic Controller
Add scanning to CubeController:
```python
with CubeController() as cube:
    colors = cube.scan()
    solution = cube.solve(colors)
    cube.execute(solution)
```
**Pros:** Single object, clean API
**Cons:** Large file, mixed concerns

### Option B: Separate Components (Current)
Keep scanner and controller separate:
```python
scanner = Scanner()
controller = CubeController()
solver = KociembaSolver()

colors = scanner.scan()
solution = solver.solve(colors)
controller.execute(solution)
```
**Pros:** Modular, testable
**Cons:** More wiring code

### Option C: Pipeline Class
Create a pipeline orchestrator:
```python
class SolvePipeline:
    def __init__(self):
        self.scanner = Scanner()
        self.controller = CubeController()
        self.solver = KociembaSolver()
    
    def run(self):
        colors = self.scanner.scan(self.controller)
        solution = self.solver.solve(colors)
        self.controller.execute(solution)
```
**Pros:** Clean separation + unified interface
**Cons:** Another abstraction layer

**Recommendation:** Option C - Pipeline class

## Speed Budget

Current estimated solve time (conservative timings):
- Scan 6 faces: ~45 seconds
- API color detection: ~5 seconds
- Kociemba solve: <1 second
- Execute 20 moves: ~120 seconds (6s per move avg)
- **Total: ~3 minutes**

Target after optimization:
- Scan 6 faces: ~25 seconds
- Local YOLO detection: <1 second
- Kociemba solve: <1 second
- Execute 20 moves: ~60 seconds (3s per move avg)
- **Target: ~1.5 minutes**

World record robots: <1 second. We're not competing with that!

## Questions to Resolve

1. Should scanner be part of CubeController or separate?
2. How to handle the y/yp rotation state during scanning?
3. Should we track physical cube orientation or logical face mapping?
4. What's the minimum viable training set size?
5. Fallback if YOLO fails - retry? API? manual?

## Next Session Priorities

1. ⏱️ Run calibrate_timing.py
2. 🧪 Test cube_controller.py with R U R'
3. 🔧 Fix any rotation bugs found
4. 📷 Collect 10+ more training scans
5. 🔄 Update auto_solve.py to use CubeController
