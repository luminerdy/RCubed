# RCubed - Path to Completion

**Created:** 2026-05-06
**Status:** Active plan — supersedes BRAINSTORM.md and NEXT-STEPS.md for ordering

## Project Definition

"Complete" means: place a scrambled cube → press one button → robot scans, solves, and executes autonomously. No internet, no human verification. Reliable enough to demo.

The vision model is the critical path — everything else is integration and polish.

---

## Phase 0 — Validate (1 session, ~1 hour)

**Goal:** Confirm the freshly-set-up Pi runs the existing code correctly before building on top.

| Task | Acceptance |
|------|------------|
| Run `test_grippers.py` end-to-end | Robot finishes in load position, no collisions, state file written |
| Verify `config/robot_state.json` was written | File exists, `clean: true`, timestamp recent |
| Run `scan_v7.py` with a solved cube | 6 face images saved, cube ends at White/Blue, state file updated |
| Run `cube_controller.py "R U R'"` from scanned state | Skips safe startup, executes 3 moves cleanly |
| Set `ANTHROPIC_API_KEY` in `~/.bashrc` | `echo $ANTHROPIC_API_KEY` returns the key in a new shell |

**Why first:** Catches any regressions from the path/state changes made on 2026-05-06. Don't build on unverified ground.

---

## Phase 1 — Integrate Pipeline (1-2 sessions)

**Goal:** One command does scan → solve → execute. Update `auto_solve.py` to use `CubeController`.

| Task | Acceptance |
|------|------------|
| Read current `auto_solve.py` and `solve_cube.py` | Understand what's there vs what's missing |
| Create `src/pipeline.py` — Pipeline class | `Pipeline().solve()` does scan → vision → kociemba → execute |
| Refactor `auto_solve.py` to use Pipeline + CubeController | Replaces old move_executor logic |
| Hook `robot_state` into Pipeline | Skip safe startup mid-pipeline; invalidate on any failure |
| End-to-end test on solved cube (no scrambling) | Returns `solved` immediately, no moves executed |
| End-to-end test on lightly scrambled cube (3-5 moves) | Cube actually solves |

**Deliverable:** `python3 src/auto_solve.py` from scrambled cube → solved cube, fully autonomous (still uses Anthropic API for vision at this stage).

---

## Phase 2 — Optimize Timing (1 session, can run parallel with Phase 3)

**Goal:** 3-minute solves down to ~1.5 minutes. Quick win, low risk.

| Task | Acceptance |
|------|------------|
| Run `scripts/calibrate_timing.py` | Measures actual servo travel times |
| Tune `TIMING` constants in `cube_controller.py` | Margins of safety preserved (no missed moves) |
| Re-run a 20-move solve at new timing | Completes without USB stalls or layer misalignment |
| Commit tuned constants with measured values in commit message | Reproducible if calibration is rerun |

---

## Phase 3 — Collect Training Data (background, parallel with Phases 1-2)

**Goal:** Get from 8 labeled scans to 100+. This is slow and parallelizable.

| Task | Acceptance |
|------|------------|
| Run `cube_labeler/app.py` and verify the existing 8 scans load correctly | UI displays, all 8 valid |
| Run `collect_training_v2.py` for batches of 10-20 scans at a time | New scans saved to `training_scans/` |
| Label each batch in the web UI | Counter shows 9 of each color, validation passes |
| Vary lighting/scrambles intentionally | Mix of simple/complex patterns, consistent lighting otherwise |

**Cadence:** 1-2 batches per session in background. Stop when you hit 100 valid labeled scans.

---

## Phase 4 — Train Vision Model (1-2 sessions, gated by Phase 3 ≥ 100 scans)

**Goal:** A local YOLOv8 model that beats the API on accuracy under your specific lighting.

| Task | Acceptance |
|------|------------|
| Run `cube_labeler/export_dataset.py` | YOLO-format dataset with 80/20 train/val split |
| `pip install ultralytics` and train YOLOv8-nano | 50 epochs minimum |
| Validate on held-out scans | mAP > 95%, especially on W vs Y (the historical weak spot) |
| Save best model to `models/cube_colors_yolov8n.pt` | Versioned with date in filename |

**Decision point:** If accuracy is poor → collect more scans (back to Phase 3) or revisit lighting setup.

---

## Phase 5 — Deploy to Hailo-8 (2-3 sessions — highest risk)

**Goal:** Run the trained model on the Hailo accelerator instead of CPU. Replace API.

This is the riskiest phase because the Hailo toolchain is unfamiliar and conversion can fail in surprising ways.

| Task | Acceptance |
|------|------------|
| Install Hailo Dataflow Compiler / runtime on Pi or build host | `hailortcli` runs |
| Convert YOLOv8 → Hailo HEF format | Conversion completes, model loads on Hailo |
| Benchmark inference speed | <100ms per face vs current API roundtrip ~2s |
| Write `src/vision_hailo.py` — drop-in replacement for API call | Same interface as current vision call |
| Wire into Pipeline behind a flag | `Pipeline(vision='api')` and `Pipeline(vision='hailo')` both work |
| End-to-end solve using Hailo vision | Cube solves with no internet connection |

**Fallback plan:** If Hailo conversion fails, run YOLOv8 on Pi CPU as middle ground (still local, just slower).

---

## Phase 6 — Harden (1-2 sessions)

**Goal:** Survive failures gracefully. Demo-ready reliability.

| Task | Acceptance |
|------|------------|
| Add retry logic to Maestro communication | USB hiccup doesn't crash the solve |
| Catch mid-solve failures in Pipeline | `robot_state.invalidate()` called, clear error message |
| Validate Kociemba string before executing | Reject impossible cube states with helpful error |
| Add a "panic stop" — Ctrl-C runs `retract_all.py` cleanly | Cube doesn't fall, state invalidated |
| Run 10 consecutive solves on different scrambles | ≥9/10 succeed without manual intervention |

---

## Phase 7 — Demo Polish (1 session)

**Goal:** Single-button demo. Something worth showing.

| Task | Acceptance |
|------|------------|
| `src/demo.py` — single entrypoint, clear status output | Run it, walk away, return to solved cube |
| Optional: add a physical button trigger via GPIO | Press button → solve starts |
| Update README with end-to-end demo instructions | Someone else could clone and run it |
| Record a video of a solve | For posterity / future context |

---

## Critical Path

```
Phase 0 (validate)
   ↓
Phase 1 (integrate) ──────────────────────────────────┐
   ↓                                                   │
Phase 2 (timing)         Phase 3 (training data) ─────┤
                             ↓                         │
                         Phase 4 (train model)         │
                             ↓                         │
                         Phase 5 (Hailo deploy) ───────┤
                             ↓                         │
                         Phase 6 (harden) ─────────────┘
                             ↓
                         Phase 7 (demo)
```

**Estimated total:** 10-15 working sessions, dominated by training data collection (passive) and Hailo deployment (risky).

---

## Progress Tracking

Update this section as phases complete. Mark blockers and any deviations from the plan.

- [ ] Phase 0 — Validate
- [ ] Phase 1 — Integrate Pipeline
- [ ] Phase 2 — Optimize Timing
- [ ] Phase 3 — Collect Training Data (8/100+)
- [ ] Phase 4 — Train Vision Model
- [ ] Phase 5 — Deploy to Hailo-8
- [ ] Phase 6 — Harden
- [ ] Phase 7 — Demo Polish
