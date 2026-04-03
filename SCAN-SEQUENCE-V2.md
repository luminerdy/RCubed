# Scan Sequence V2 - Ends at White Front / Blue Top

## Goal
Design a 6-face scan that naturally returns to starting orientation.

## Key Insight
If we track total rotations, we can plan moves that cancel out.

## Rotation Tracking
- Y rotations: CW = +90°, CCW = -90°
- X rotations: Forward = +90°, Backward = -90°

**For the scan to end at start, total Y = 0° and total X = 0°**

---

## Current Sequence (broken)

| Step | Action | Y total | X total | Front face |
|------|--------|---------|---------|------------|
| Start | - | 0 | 0 | White |
| 3 | Scan Front | 0 | 0 | White |
| 4 | Y 180° | +180 | 0 | Yellow |
| 5 | Scan Back | +180 | 0 | Yellow |
| 6 | Y 90° CW | +270 | 0 | Red |
| 7 | Scan Right | +270 | 0 | Red |
| 8 | Y 180° | +450 | 0 | Orange |
| 9 | Scan Left | +450 | 0 | Orange |
| 10 | X 90° fwd | +450 | +90 | Green |
| 11 | Scan Top | +450 | +90 | Green(was D) |
| 12 | X 180° | +450 | +270 | Blue |
| 13 | Scan Bottom | +450 | +270 | Blue(was U) |

**End state:** Y=+450° (+90° net), X=+270° (-90° net)

To return: need Y -90° and X +90° (backward)

---

## New Sequence - Balanced Rotations

**Strategy:** Scan in an order that balances rotations.

| Step | Action | Y total | X total | Front | Scanning |
|------|--------|---------|---------|-------|----------|
| 1 | Scan Front | 0 | 0 | White | F (White) |
| 2 | Y 180° | +180 | 0 | Yellow | - |
| 3 | Scan Back | +180 | 0 | Yellow | B (Yellow) |
| 4 | Y -90° (CCW) | +90 | 0 | Red | - |
| 5 | Scan Right | +90 | 0 | Red | R (Red) |
| 6 | Y 180° | +270 | 0 | Orange | - |
| 7 | Scan Left | +270 | 0 | Orange | L (Orange) |
| 8 | Y -90° (CCW) | +180 | 0 | Yellow | - |
| 9 | X 90° fwd | +180 | +90 | Green | - |
| 10 | Scan Bottom | +180 | +90 | Green | D (Green) |
| 11 | X -180° (back) | +180 | -90 | Blue | - |
| 12 | Scan Top | +180 | -90 | Blue | U (Blue) |
| 13 | X 90° fwd | +180 | 0 | Yellow | - |
| 14 | Y -180° | 0 | 0 | White | - |

**End state:** Y=0°, X=0° → Back to White front, Blue top! ✓

---

## Even Simpler - Minimize resets

Let me think about gripper positions too...

Actually, here's the simplest approach:

### Sequence V2

**Start:** F=White, U=Blue, grippers 2&8 at C/A

1. **Scan FRONT** (White)
2. **Y 180°** (2:C→A, 8:A→C) → F=Yellow
3. **Scan BACK** (Yellow)
4. **Y CCW 90°** (reset to B, then 2:B→C, 8:B→A) → F=Red
5. **Scan RIGHT** (Red)
6. **Y 180°** (2:C→A, 8:A→C) → F=Orange
7. **Scan LEFT** (Orange)
8. **Y CCW 90°** (reset to B, then 2:B→C, 8:B→A) → F=Yellow
   - Now we're back at Y=0° relative to start on Y axis, but F=Yellow (180° from White)
   - Wait, let me recalculate...

Hmm, this is getting confusing. Let me trace more carefully:

### Careful Trace

**Start:** F=White, U=Blue, R=Red, L=Orange, B=Yellow, D=Green

**Step 1: Scan FRONT** → Captures White
State: F=White, U=Blue, R=Red, L=Orange

**Step 2: Y 180°** (grippers 2:C→A, 8:A→C)
Y 180°: F↔B, R↔L
State: F=Yellow, U=Blue, R=Orange, L=Red

**Step 3: Scan BACK** → Captures Yellow (was B, now F)

**Step 4: Y CCW 90°** (need reset first: 2:A→B, 8:C→B, then 2:B→C, 8:B→A)
Y CCW: F→R, R→B, B→L, L→F
Before: F=Yellow, R=Orange, B=White, L=Red
After: F=Red, R=Yellow, B=Orange, L=White
State: F=Red, U=Blue, R=Yellow, L=White

**Step 5: Scan RIGHT** → Captures Yellow... wait, that's wrong!

We want to scan the RED face (original R), but after Y CCW from step 4:
- Original R (Red) is now... let me trace.

From start: R=Red
After Y 180° (step 2): R=Orange (swapped with L)
After Y CCW 90° (step 4): what was R becomes B

Ugh, this is confusing. Let me think differently.

---

## Alternative: Track which ORIGINAL face is in front

| Step | Move | Original face now in front |
|------|------|---------------------------|
| Start | - | F (White) |
| 1 | Scan | F ✓ |
| 2 | Y 180° | B (Yellow) |
| 3 | Scan | B ✓ |
| 4 | Y CW 90° | L (Orange) |
| 5 | Scan | L ✓ |
| 6 | Y 180° | R (Red) |
| 7 | Scan | R ✓ |
| 8 | Y CW 90° | B (Yellow) - already scanned |
| - | X fwd 90° | D (Green) |
| 9 | Scan | D ✓ |
| 10 | X 180° | U (Blue) |
| 11 | Scan | U ✓ |

Now to return from here:
- After step 11: Total Y = 180+90+180+90 = 540° = 180° net
- After step 11: Total X = 90+180 = 270° = -90° net

To return: Y -180°, X +90°

| Step | Move | Cumulative |
|------|------|------------|
| 12 | X -90° (backward) | X = 0 |
| 13 | Y -180° | Y = 0 |

Final: Back at start! F=White, U=Blue ✓

---

## Final Sequence

1. Scan F (White)
2. Y 180° → scan B (Yellow)  
3. Y CW 90° → scan L (Orange)
4. Y 180° → scan R (Red)
5. Y CW 90° + X fwd 90° → scan D (Green)
6. X 180° → scan U (Blue)
7. X back 90° + Y 180° → return to start

This should work!
