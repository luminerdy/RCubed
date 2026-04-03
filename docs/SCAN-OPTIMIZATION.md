# Optimizing the Scan Sequence

## Current Approach
We scan faces by rotating the cube, then try to return to start orientation.

**Current sequence:**
1. Front (no move)
2. Back (Y 180°)
3. Right (Y 90° after resetting)
4. Left (Y 180°)
5. Top (X 90°)
6. Bottom (X 180°)
7. Return to start (multiple moves)

**Problem:** Returning to start requires figuring out complex inverse rotations.

---

## Better Approach: Don't return to start!

**Why do we need White front / Blue top after scan?**
- For the SOLVE to work correctly
- The solver assumes a specific orientation

**But wait:** The scan images tell us EXACTLY what colors are where. We just need to:
1. Know what orientation the cube ends up in
2. Tell the solver that orientation

**OR even simpler:**
- Track orientation during scan
- End in a KNOWN state (any state)
- Map the scanned faces to the correct Kociemba positions

---

## Simplest Scan Sequence

**Goal:** Scan all 6 faces with minimum moves, end in a KNOWN state.

### Option A: Scan in pairs, minimal resets

```
Start: F=White, U=Blue (grippers 2&8 at C/A)

1. SCAN FRONT (White) - no move
2. Y 180° (2:C→A, 8:A→C)
3. SCAN BACK (Yellow) - now front

   (At this point: F=Yellow, U=Blue, R=Orange, L=Red)

4. Y 90° CW (reset 2&8 to B, then 2:B→A, 8:B→C)
5. SCAN RIGHT (Red) - was left, now front

   (At this point: F=Red, U=Blue, R=Yellow, L=White)

6. Y 180° (2:A→C, 8:C→A)  
7. SCAN LEFT (Orange) - was right, now front

   (At this point: F=Orange, U=Blue, R=White, L=Yellow)

8. X 90° forward (reset, then 0:B→C, 6:B→A)
9. SCAN TOP (Blue) - was top, now front

   (At this point: F=Blue, U=Orange, R=White, L=Yellow)

10. X 180° (0:C→A, 6:A→C)
11. SCAN BOTTOM (Green) - was bottom, now front

   FINAL STATE: F=Green, U=Orange, R=White, L=Yellow, B=Blue, D=Red

   Wait, that's not right. After X 180° from F=Blue,U=Orange:
   X 180°: F↔B, U↔D
   So: F=?, let me recalculate...
```

Actually the current scan sequence IS already pretty optimal for capturing. The issue is just the return.

---

## Solution: Track orientation, don't return

After scanning, we know:
- Cube ended at some orientation
- We know WHAT that orientation is from the choreography

**For solving:**
1. Don't move cube back
2. Adjust move execution to account for current orientation

**OR even simpler:**
1. End scan with cube in a consistent, SIMPLE state
2. Document what that state is
3. Solve from that state

---

## Recommended: Just remove Step 14

After Step 13, cube is at: **F=Blue, U=Red, R=White, L=Yellow, B=Green, D=Orange**

Instead of trying to return to F=White/U=Blue:
1. Track this orientation
2. Before solving, do a simple manual return (or automated)
3. OR adjust solver to work from any orientation

**For now:** Just do ONE simple return move sequence that we KNOW works:

From: F=Blue, U=Red, R=White
To: F=White, U=Blue

This requires:
- Y CW 90° (White to front) → F=White, U=Red
- Z CCW 90° (Blue to top) → But we can't do Z easily!

Actually X backward works:
- From F=Blue, U=Red: X backward (B→U) gives U=Green, not Blue!

Hmm, the orientation math is tricky. Let me trace through the ACTUAL scan step by step...

---

## Actual Trace

**Start:** F=White, U=Blue, R=Red, L=Orange, B=Yellow, D=Green

**After Step 4-5 (Y 180°):**
F=Yellow, U=Blue, R=Orange, L=Red, B=White, D=Green

**After Step 6 (Y CW 90°):**
F=Red, U=Blue, R=Yellow, L=White, B=Orange, D=Green

**After Step 8-9 (Y 180°):**
F=Orange, U=Blue, R=White, L=Yellow, B=Red, D=Green

**After Step 10 (X forward 90°):**
X forward: F→U, U→B, B→D, D→F
F=Green, U=Orange, R=White, L=Yellow, B=Blue, D=Red

**After Step 12-13 (X 180°):**
X 180°: F↔B, U↔D
F=Blue, U=Red, R=White, L=Yellow, B=Green, D=Orange

**So after scan:** F=Blue, U=Red, R=White, L=Yellow, B=Green, D=Orange

**To get to F=White, U=Blue:**
- White is currently R (right)
- Blue is currently F (front)

Option 1: Y CCW 90° (R→F): F=White, U=Red, R=Green, L=Yellow
Then: X CCW 90° (or "backward"): Hmm, need to think about this axis...

Actually I realize the confusion - let me think about which axis is which:
- Y axis = vertical (top to bottom) - Y rotation spins around this
- X axis = left to right - X rotation (tumble) spins around this
- Z axis = front to back - Z rotation spins around this (but we can't do this easily)

From F=Blue, U=Red, R=White:
- Y CCW 90°: F=White, U=Red, L=Blue, R=Green
  - Now U=Red, need Blue on top
  - Blue is on L
- Then... we'd need Z to get Blue from L to U, which we can't do

From F=Blue, U=Red, R=White:
- X backward 90° first (U→F): F=Red, U=Green, R=White, D=Blue
  - Nope, Blue went to D

Let me try:
- Y CW 90°: F=Yellow... wait no

Current: F=Blue, U=Red, R=White, L=Yellow, B=Green, D=Orange

Y CW 90° (R→F): F=White, U=Red, R=Blue... wait
- After Y CW: what was R becomes F, what was F becomes L, what was L becomes B, what was B becomes R
- So: F=White✓, U=Red (unchanged), R=Blue, L=Green, B=Yellow, D=Orange

Now need Blue on top. Blue is on R.
- X "roll right"? We can't do that easily.
- Z rotation would do it, but no Z.

This is why it's complicated!

---

## The Real Solution

**DON'T try to return to original orientation!**

Instead:
1. After scan, note the orientation
2. The solve_cube.py can work from ANY orientation as long as it knows what it is
3. OR: manually place cube correctly before solving

For now, let's just:
1. Remove Step 14 entirely
2. Document the end state
3. Fix the solver to handle it (or manually reorient)
