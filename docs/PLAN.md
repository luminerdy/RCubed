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

### 2. Robot layer — code done, hardware check pending
`rcubed/robot.py`, `choreography.py`, `cube_model.py`, tests, simulator, CLI.

Hardware acceptance, in order, with **no cube** in the robot first:
1. `python3 -m rcubed safe-start` — fingers end at B, all released, no contact.
2. `python3 -m rcubed load` — 2 goes to C, 8 to A.
3. With a **solved** cube inserted: `grip`, then `move "R"`, check the right face turned
   clockwise as seen from the right. Same for `L`, `U`, `D`.
4. `move "y"` with `--no-home`: confirm the red (right) face came to the front. Then `x`.
   If either goes the wrong way, flip the letters in `config/robot.json → rotations`.
5. `move "R U R' U' R U R' U' R U R' U' R U R' U' R U R' U' R U R' U'"` — six sexy moves
   return a solved cube to solved. This proves turn directions and F/B handling together
   once `F` and `B` are included: `move "F R U R' U' F'"` twice.

### 3. Scanner
- Camera capture with locked exposure/white balance and a higher resolution than 640×480.
- Scan choreography producing six face images, each tagged with the physical face it shows.
- Because the cube model is physical-frame, the expected sticker order for each image is
  read straight from the model (no hand-derived rotation corrections).

### 4. Vision (the part that failed before)
- Feature extraction: for each of the 9 grid cells, the mean and spread of colour in a
  central patch (LAB and HSV), plus the same features normalised against the frame's
  white centre to cancel lighting drift.
- **Self-labelled data.** Insert a solved cube; every scan is labelled for free. Then the
  robot applies random moves it tracks in the model, scanning after each, so every image
  carries ground-truth labels with no manual clicking. Target 50–100 scans under the
  final lighting.
- Classifier: k-nearest-neighbours or a small multinomial logistic regression on the
  features; evaluated on held-out scans. Falls back to nothing: if accuracy is not 100%
  on held-out data, fix lighting or features, not the model size.
- **Constrained assignment.** All 54 stickers are assigned at once under the rule of
  exactly 9 per colour, with centres known; then the state must be accepted by Kociemba.
  Ambiguous orange/red and white/yellow stickers get resolved by the counts.

### 5. Pipeline
- `python3 -m rcubed solve`: scan → classify → Kociemba → execute → verify by re-scanning.
- Retry on Maestro USB errors; Ctrl-C safe stop (already in the CLI).
- Ten consecutive solves on different scrambles without intervention.

### 6. Later, optional
- **Lazy resets.** Do not return a gripper to B after every turn; turn from wherever
  it is parked. Half turns never need a reset (A↔C, B↔D). Quarter turns only need
  one at the ends of the range (clockwise from D, counter-clockwise from A). A finger
  parked at A or C still blocks its neighbours from turning to A or C, so the
  collision guard decides when a reset is forced.
- Replace fixed sleeps with position polling to speed up moves.
- Timing calibration.
- A physical start button.

## Testing rule

Everything above the backend runs off-robot against the simulator. The tests must pass
on any machine before code is tried on the hardware.
