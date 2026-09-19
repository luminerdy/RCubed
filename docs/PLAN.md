# Restart plan (September 2026)

**Goal.** Place a scrambled cube, run one command, get a solved cube. All code is
plain Python that runs on the Pi with no network. Nothing depends on an LLM.

**Decisions made 2026-09-15**

- Same repository. Old code lives under `legacy/` (tag `v0-legacy`) for reference and is
  deleted once the new code covers it.
- Calibration values from April 2026 are trusted; no mechanical changes since.
- The Hailo-8 is not used. Colour classification of 54 patches is trivial on the CPU.
- No YOLO. Sticker positions are fixed by the rig, so vision is patch classification.
- Lighting: a ring light around the camera (not yet mounted). Neutral white, diffuse,
  fixed brightness. Needed before any vision data is collected, not before.
- Cube: stickered, logo on the white centre. Centres are never classified; the scan
  order says which face is which.

## Phases

### 1. Housekeeping — done
- Pi commits pushed, `v0-legacy` tagged, token removed from the Pi's git remote.
- **Still yours:** revoke that GitHub token in GitHub settings and delete `~/github.txt`
  and `~/RootPW.txt` on the Pi.

### 2. Robot layer — done
`rcubed/robot.py`, `choreography.py`, `cube_model.py`, tests, simulator, CLI.

Verified on the robot 2026-09-16/17: safe startup, load pose, all 18 face moves
(quarter, prime and half on every face, F/B via spin), `y`/`y'`/`x`/`x'`, pair resets.

The acceptance steps that were used, for reference:
1. `python3 -m rcubed safe-start` — fingers end at B, all released, no contact.
2. `python3 -m rcubed load` — 2 goes to C, 8 to A.
3. With a **solved** cube inserted: `grip`, then `move "R"`, check the right face turned
   clockwise as seen from the right. Same for `L`, `U`, `D`.
4. `move "y"` with `--no-home`: confirm the red (right) face came to the front. Then `x`.
   If either goes the wrong way, flip the letters in `config/robot.json → rotations`.
5. `move "F R U R' U' F'"` then its inverse `move "F U R U' R' F'"` returns a solved cube
   to solved. (Result 2026-09-17: run twice instead of with the inverse, the robot produced
   exactly the state the model predicts, `B B R / W W W / W W W` on the front.)

### 3. Scanner — done
Verified on the robot 2026-09-17/18: 6-face scan from the load pose (`photo, y2, photo,
x', photo, x2, photo, y, photo, y2, photo`), 1280×960 MJPG, crop box measured from a real
snapshot. Because the cube model is physical-frame, expected sticker order per image is
read straight from the model — no hand-derived rotation corrections.

### 4. Vision — done, first real scan reads clean
`rcubed/vision.py`: median L\*a\*b\* per cell → Gaussian classifier (class means + pooled
covariance) → constrained assignment (exactly 8 non-centre stickers per colour, centres
known from the choreography). `collect` scans a known cube, applies a tracked scramble,
repeats — self-labelled, no manual clicking. `train` fits the model; `read`/`solve`
classify a scan and hand it to the solver. First real scan on 2026-09-17: 52/54 correct
unconstrained, 54/54 after the count constraint.

Still open: collect a proper training set (`collect --count ~20`) under final lighting
once the ring light is mounted, and re-train.

### 5. Pipeline — mostly done
`solve` does scan → classify → Kociemba → execute (`--dry-run` stops before moving).
Not yet done: verify-by-rescan after execution, retry on Maestro USB errors, ten
consecutive solves on different scrambles.

### 6. Speed tuning — next session (2026-09-19)
Context: the robot works correctly but is slow to watch, most of it fixed `time.sleep()`
padding carried over unmeasured from the legacy code. Two fixes already landed
(2026-09-18): synchronised rotation-pair speeds (`_synced_speeds` — the old fixed
0=60/6=45 split was guesswork, not proportional to actual travel, and let the middle
slice twist against the outer layers) and a direct `x2` toggle that skips a reset.

**No true position feedback exists.** `get_position()`/`get_moving_state()` only reflect
the Maestro's own commanded trajectory, not anything sensed from the servo — DS3218 is a
plain 3-wire servo. So speed increases must be tuned incrementally with someone watching
the hardware, not automated blindly; going too fast fails silently (the Maestro reports
"done" on schedule even if the gripper hasn't physically arrived).

Plan: raise `speeds.rotation.x` / `.y` (currently 60) a step at a time, and separately
try lowering `timing.turn_90`, `turn_180`, `x_rotation`, `y_rotation`, `gripper_move`
(currently 1.2/2.0/2.5/2.0/0.8s) — watch each change on a solved cube for lag, twist, or
stall before keeping it. Settle on the fastest values that still look clean.

### 7. Later, optional
- **Lazy resets.** Do not return a gripper to B after every turn; turn from wherever
  it is parked. Half turns never need a reset (A↔C, B↔D, and now A↔C for x2 too — see §6
  history). Quarter turns only need one at the ends of the range (clockwise from D,
  counter-clockwise from A). A finger parked at A or C still blocks its neighbours from
  turning to A or C, so the collision guard decides when a reset is forced.
- Camera-based move verification (compare a photographed face against the expected
  layout) as a substitute for the position feedback the hardware doesn't have.
- A physical start button.

## Testing rule

Everything above the backend runs off-robot against the simulator. The tests must pass
on any machine before code is tried on the hardware.
