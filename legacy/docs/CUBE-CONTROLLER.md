# Cube Controller - Modular Robot Control

## Overview

`cube_controller.py` provides a clean, stateful interface for controlling the RCubed robot using **standard cube notation**. It handles all the complexity of gripper management, orientation tracking, and F/B move optimization internally.

## Standard Cube Notation

### Face Turns

| Move | Meaning | Gripper |
|------|---------|---------|
| R, R', R2 | Right face CW, CCW, 180° | 6 (direct) |
| L, L', L2 | Left face | 0 (direct) |
| U, U', U2 | Up face | 2 (direct) |
| D, D', D2 | Down face | 8 (direct) |
| F, F', F2 | Front face | 6 (after y rotation) |
| B, B', B2 | Back face | 6 (after y' rotation) |

### Whole Cube Rotations

| Move | Meaning | Physical Action |
|------|---------|-----------------|
| x | Rotate on R axis (top → front) | 0:B→C, 6:B→A |
| x' | Rotate on R axis (bottom → front) | 0:B→A, 6:B→C |
| y | Rotate on U axis (right → front) | 2:B→A, 8:B→C |
| y' | Rotate on U axis (left → front) | 2:B→C, 8:B→A |

## The F/B Problem

RCubed has **no gripper on Front or Back faces**. To turn F or B, we must:

1. Rotate the whole cube so F (or B) is at the R position
2. Turn using the R gripper
3. Optionally rotate back

### Naive Approach (Slow)
```
F F' R B → y R yp | y R' yp | R | yp R y
         = 8 extra rotations
```

### Optimized Approach (Fast)
```
F F' R B → y R R' | yp R | yp R | y (restore at end)
         = 3 rotations
```

The controller tracks `robot_orientation` ('normal', 'y', or 'yp') and only transitions when needed.

## Usage

### Python API

```python
from cube_controller import CubeController

with CubeController() as cube:
    # Individual moves
    cube.R()       # Right CW
    cube.Rp()      # Right CCW (prime)
    cube.R2()      # Right 180°
    
    # F/B work automatically
    cube.F()       # Rotates cube, turns, stays rotated
    cube.F2()      # Already rotated - just turns
    
    # Whole cube rotations
    cube.x()       # Tumble forward
    cube.y()       # Spin (right → front)
    
    # Execute full solution
    cube.execute("R U R' F2 B L2")
    
    # Check state
    cube.status()
```

### Command Line

```bash
# Single moves
python3 src/cube_controller.py R U R'

# Full solution
python3 src/cube_controller.py "R U R' F2"

# Cube rotations
python3 src/cube_controller.py x y x'
```

## State Tracking

The controller tracks:

| State | Description |
|-------|-------------|
| `gripper_pos` | Position (A/B/C/D) of each gripper servo |
| `rp_status` | Hold/retracted status of each RP servo |
| `cube` | CubeOrientation object (which color on each face) |
| `robot_orientation` | 'normal', 'y', or 'yp' |
| `move_count` | Total operations executed |

## Architecture

```
CubeController
├── Hardware Layer
│   ├── _set_gripper(servo, pos)
│   ├── _set_rp(rp, state, speed)
│   ├── engage(*grippers)
│   └── retract(*grippers)
├── Primitives
│   ├── _do_y(), _do_yp(), _do_y2()
│   ├── _do_x(), _do_xp(), _do_x2()
│   └── _turn(gripper, direction)
├── Orientation Management
│   ├── _transition_to(target)
│   └── _orientation_for_face(face)
└── Public API
    ├── R(), Rp(), R2(), L(), Lp(), L2()
    ├── U(), Up(), U2(), D(), Dp(), D2()
    ├── F(), Fp(), F2(), B(), Bp(), B2()
    ├── x(), xp(), x2(), y(), yp(), y2()
    └── execute(solution)
```

## Integration with Kociemba Solver

```python
import kociemba
from cube_controller import CubeController

# Get solution from Kociemba
cube_string = "DRLUUBFBRBLURRLRUBLRDDFDLFUFUFFDBRDUBRUFLLFDDBFLUBLRBD"
solution = kociemba.solve(cube_string)
# Returns: "R U R' F2 D' L2 ..."

# Execute on robot
with CubeController() as cube:
    cube.execute(solution)
```

## Timing

Default timing values (can be tuned):

| Operation | Time |
|-----------|------|
| Gripper move | 0.8s |
| RP engage | 2.0s |
| RP retract | 2.0s |
| 90° turn | 1.2s |
| 180° turn | 2.0s |
| X rotation | 2.5s |
| Y rotation | 2.0s |

## Design Decisions

1. **State tracking**: Every operation updates internal state. No need to manually track gripper positions.

2. **Self-preparing**: Each move handles its own prep. Call `F()` and it just works.

3. **Optimization**: F/B moves don't restore orientation immediately. Multiple F moves share one rotation.

4. **Standard notation**: Uses cubing community standard (R, R', R2, x, y, z).

5. **Context manager**: `with CubeController() as cube:` handles connect/disconnect.
