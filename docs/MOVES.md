# Move reference

Everything the `move` command accepts, and what the robot does for each token.
(Same content as [moves.html](moves.html), which renders when opened in a browser.)

```bash
python3 -m rcubed move "R U R' U'"          # several tokens, space separated
python3 -m rcubed move --no-home "y"        # leave the cube rotated at the end
python3 -m rcubed --sim -v move "F2 B'"     # simulate, print the servo trace
```

## The robot

```
              camera
                ↓
           gripper 2   top     turns U   arm 3
     gripper 0   ■   gripper 6
       left            right
      turns L         turns R
      arm 1           arm 7
           gripper 8   bottom  turns D   arm 9
```

Even channels rotate; the odd channel one higher is that gripper's rack-and-pinion arm.
Front and back have no gripper.

**Finger positions.** Each gripper has four positions about 90° apart: `A B C D`.
`B` is neutral. From B: `C` = 90° clockwise (looking at that face), `A` = 90°
counter-clockwise, `D` = 180°. Fingers at A or C are out of the camera's view; at B or D
they are in it.

**Load orientation.** White front, blue top, red right (orange left, green bottom, yellow back).

## Face turns

These are what a solution is made of. Plain = 90° clockwise looking at that face,
`'` = 90° counter-clockwise, `2` = 180°.

| Tokens | Face | How the robot does it |
|---|---|---|
| `U` `U'` `U2` | top | gripper 2 turns B→C / B→A / B→D, then resets to B |
| `D` `D'` `D2` | bottom | gripper 8, same pattern |
| `R` `R'` `R2` | right | gripper 6, same pattern |
| `L` `L'` `L2` | left | gripper 0, same pattern |
| `F` `F'` `F2` | front | spins the cube `y'` so the front face reaches the right gripper, then gripper 6 turns |
| `B` `B'` `B2` | back | spins the cube `y` so the back face reaches the right gripper, then gripper 6 turns |

A face letter always means the face *currently at that position on the robot*, not a
colour. After the cube has been rotated, `R` is whatever is on the right now. Consecutive
`F` and `B` moves share one spin: after `y'` the front is at the right gripper and the back
is at the left one.

**One face turn, step by step**

1. All four arms hold.
2. The turning gripper goes B→C, B→A or B→D. Wait for the turn to complete.
3. That gripper's arm retracts (fast). The other three keep holding.
4. The finger swings back to B.
5. The arm re-engages (slowly, so it does not shove the cube).

## Whole-cube rotations

Never part of a solution. Useful for testing, and the scanner uses them between photographs.

| Token | Effect | Servos |
|---|---|---|
| `y` | spin like a U turn: the **right** face comes to the front | 2 to C, 8 to A; top and bottom arms hold, left and right release |
| `y'` | the **left** face comes to the front | 2 to A, 8 to C |
| `y2` | half spin: the **back** face comes to the front | toggles 2 and 8 between A and C |
| `x` | tumble like an R turn: the **front** face goes to the top | 0 to A, 6 to C; left and right arms hold, top and bottom release |
| `x'` | the **top** face comes to the front | 0 to C, 6 to A |
| `x2` | half tumble | two `x` moves with a reset between |
| `z` | not available: the robot cannot do it | rejected with an error |

Verified on hardware 2026-09-17: all 18 face moves, `y`, `y'`, `x` and `x'`.

## What every `move` does around the tokens

1. Restores the saved state from `config/robot_state.json`, or runs a safe startup if it
   is unknown (after a reboot, a crash, Ctrl-C or `retract`). **Safe startup releases all
   four arms**: hold the cube by hand if one is loaded.
2. Before each face turn: engages all arms and resets any parked fingers to B, in opposite
   pairs (top and bottom together while left and right hold, and vice versa).
3. After the last token, unless `--no-home`: spins the cube back to its starting
   orientation with the fewest x/y moves, resets all fingers to B, all four arms holding.
4. Prints the servo positions and where each face now sits, and saves the state.

## Options

| Flag | Meaning |
|---|---|
| `--no-home` | Leave the cube in its final orientation instead of spinning it back. Face turns are never undone; this only concerns the orientation of the whole cube. |
| `--sim` | Run in the simulator, no hardware. Reports the time the robot would have taken. |
| `-v` | Verbose. With `--sim`, prints every servo command. |
| `--port` | Maestro command port, if auto-detection needs overriding. |

## Other commands

| Command | What it does |
|---|---|
| `status` | Show the remembered finger and arm positions and the cube's orientation. Moves nothing. |
| `safe-start` | From unknown positions to all fingers at B, all arms released, in a collision-free order. Releases the cube. |
| `load` | Loading pose: left and right at B, top at C, bottom at A, arms released. Insert the cube white front, blue top, red right. |
| `grip` | Engage all four arms slowly. |
| `release` | Retract all four arms. |
| `retract` | **Emergency.** Retract everything at full speed and forget the state; the next command runs a safe startup. |
| `servo <ch> <us>` | Raw pulse width to one channel, for calibration only. Forgets the state. |

## Checklist with a solved cube

1. `move "R"` then `move "R'"`: a red column appears on the right of the white face, then
   the cube is solved again. Repeat for U, L, D, then one `R2`.
2. `move --no-home "y"`: red comes to the front. `move "y'"` undoes it.
3. `move --no-home "x"`: white goes to the top. `move "x'"` undoes it.
4. `move "F"` then `move "F'"`: spin, turn, spin home; cube solved again.
5. `move "F R U R' U' F'"` twice: everything at once; must end solved.

If step 1 turns the wrong way, swap `C` and `A` under `turn` in `config/robot.json`. If
step 2 or 3 goes the wrong way, swap the letters under `rotations`. Calibration numbers
live only in that file.
