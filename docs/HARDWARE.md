# Hardware reference

Distilled from `legacy/docs/RULES.md` and the working code. Everything below was
re-verified on the robot after the restart (2026-09-16/17) unless marked otherwise.

## Physical layout

```
              camera
                ↓
        ┌───────────────┐
        │   gripper 2   │   top     (servo 2, RP 3)   turns U
        │       ↓       │
        │  0 →  ■  ← 6  │   left 0 (RP 1) turns L    right 6 (RP 7) turns R
        │       ↑       │
        │   gripper 8   │   bottom  (servo 8, RP 9)   turns D
        └───────────────┘
```

- Even Maestro channels are gripper (rotation) servos, odd channels are the
  rack-and-pinion (RP) servos that push the gripper onto the cube. Channels 4, 5, 10, 11 unused.
- The camera looks at the F face from the front. F and B have no gripper.
- Standard load orientation: **white front, blue top, red right** (orange left, green bottom, yellow back).

## Servo positions

Gripper servos have four positions, ~90° apart. All four follow the same pattern
from the perspective of the face they hold:

| From B | Result |
|--------|--------|
| B → C  | 90° clockwise |
| B → A  | 90° counter-clockwise |
| B → D  | 180° |

RP servos have two positions: `retracted` (clear of the cube) and `hold`.
Engage slowly (speed 30) so the fingers do not shove the cube; retract fast (speed 0).

Numbers: `config/robot.json`. They match the values verified 2026-04-03.

## Face turn

1. All four RPs hold.
2. Turning gripper: B → C / A / D. Wait `turn_90` or `turn_180`.
3. Retract that gripper's RP. Wait `rp_retract`.
4. Gripper back to B. Wait `gripper_move`.
5. Re-engage the RP slowly. Wait `rp_engage`.

## Whole-cube rotations

| Rotation (standard notation) | Effect | Servos | Holding | Released |
|---|---|---|---|---|
| `y`  | R → F | 2: B→C, 8: B→A | RPs 3 & 9 | RPs 1 & 7 |
| `y'` | L → F | 2: B→A, 8: B→C | RPs 3 & 9 | RPs 1 & 7 |
| `x`  | F → U | 0: B→A, 6: B→C | RPs 1 & 7 | RPs 3 & 9 |
| `x'` | U → F | 0: B→C, 6: B→A | RPs 1 & 7 | RPs 3 & 9 |

- All four rotations and all 18 face moves (including F/B via a spin) were verified on
  the robot on 2026-09-17 with a solved cube.
- `y2` can be done by toggling 2 and 8 between A and C (verified in the old scan sequence).
  `x2` is done as two `x` moves with a reset between them.
- x rotations run with speed limits (servo 0 = 60, servo 6 = 45) so the two servos stay in sync.
- Always engage the new holding pair **before** releasing the other pair.

## Collision rule

Adjacent grippers (0–2, 0–8, 6–2, 6–8) collide if both are at A, or both at C, and a
finger sweeping through C can hit a neighbour parked at C. Opposite grippers never collide.

**Rule enforced in code:** a gripper may move to, or through, A or C only while both
adjacent grippers are at B or D.

Consequences: only one opposite pair may be off B/D at a time; a rotation with 2 & 8
requires 0 & 6 at B (and vice versa); before a face turn every gripper goes back to B.

## Safe startup (unknown state)

After power-on, a crash, or an emergency retract, nobody knows where the fingers are.

1. Retract all four RPs fast (max clearance).
2. Move 0 and 6 to B together (opposite pair; cannot hit each other).
3. Move 2 and 8 to B together (safe now that 0 and 6 are at B).

`config/robot_state.json` remembers the positions between runs and is ignored if it
predates the last boot or a run was interrupted, so this only happens when needed.

## Camera

- SunplusIT USB webcam on `/dev/video0`. Defaults to 640×480; supports up to 2592×1944 (MJPG).
- Fingers at B and D are in the camera's view; at A and C they are clear.
  Side faces are scanned with 2 & 8 at A/C; top and bottom after an x with 0 & 6 at A/C.
- Legacy face crop in a 640×480 frame: x 180–460, y 75–400 (`config/robot.json → camera.crop`).
- Lock exposure and white balance before scanning; the auto modes drift between faces.

## Known issues from the previous build

- Maestro occasionally stops responding over USB. Power-cycle it (or reboot the Pi).
- Fingers can catch a layer edge on engagement, and repeated moves let the cube creep
  downward. Foam-tape fingers with filed edges helped; rubber bands were the earlier fix.
- Blue/purple LED lighting made white and yellow indistinguishable. Use neutral white light.

## Power (to be recorded)

Eight DS3218 servos can draw several amps under load. Record the servo supply, how it
feeds the Maestro rail, and the state of the Maestro's VSRV=VIN jumper here.
