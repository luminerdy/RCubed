# Scan Sequence - Final Design

## Physical Setup
- Camera faces FRONT of cube
- Grippers 0 & 6 (left/right) do X rotations (tumble forward/backward)
- Grippers 2 & 8 (top/bottom) do Y rotations (spin left/right)
- RP 1 & 7 hold cube during Y rotations
- RP 3 & 9 hold cube during X rotations

## Start Position
- White front, Blue top (standard orientation)
- Grippers 0, 2, 6, 8 at B position
- All RP retracted

## Sequence

### Phase 1: Four side faces (Y rotations only)

**Step 1: Scan FRONT (White)**
- No rotation needed
- Camera sees: White

**Step 2: Y 180° → Scan BACK (Yellow)**
- Grippers 2&8 rotate 180° (C→A / A→C or similar)
- Camera sees: Yellow

**Step 3: Y 90° CW → Scan RIGHT (Red)**
- Reset grippers to B, then rotate 90°
- After Y 180° + Y 90° = Yellow rotated 90° CW = Red in front
- Wait... let me trace this properly.

Actually, let me trace face positions:

**Start:** F=White, B=Yellow, R=Red, L=Orange, U=Blue, D=Green

**After Y 180°:** F↔B, R↔L
- F=Yellow, B=White, R=Orange, L=Red

**After Y CW 90° (from Yellow front):** R→F, F→L, L→B, B→R
- Before: F=Yellow, R=Orange, L=Red, B=White
- After: F=Orange, R=White, L=Yellow, B=Red

That's not what we want! We want Red in front.

Let me restart with Y CCW instead:

**After Y 180°:** F=Yellow, R=Orange, L=Red, B=White
**After Y CCW 90°:** L→F, F→R, R→B, B→L
- Before: F=Yellow, L=Red, R=Orange, B=White  
- After: F=Red, L=White, R=Yellow, B=Orange

Now F=Red ✓

**After Y 180°:** F↔B, R↔L
- Before: F=Red, B=Orange, R=Yellow, L=White
- After: F=Orange, B=Red, R=White, L=Yellow

Now F=Orange ✓

**Return to start from here:**
- Current: F=Orange, B=Red, R=White, L=Yellow, U=Blue, D=Green
- Need: F=White, B=Yellow, R=Red, L=Orange

Y CCW 90°: L→F, F→R, R→B, B→L
- Before: F=Orange, L=Yellow, R=White, B=Red
- After: F=Yellow, L=Red, R=Orange, B=White

Not there yet. Another Y CCW 90°:
- Before: F=Yellow, L=Red, R=Orange, B=White
- After: F=Red, L=White, R=Yellow, B=Orange

Still not. Total Y so far: 180 + 90 + 180 + 90 + 90 = too many.

## Simpler Approach

**Phase 1: Scan F, B, R, L with minimal Y rotations**

1. Scan F (White) - no move
2. Y CW 90° → Scan R (Red)  [Y total: +90]
3. Y CW 90° → Scan B (Yellow) [Y total: +180]
4. Y CW 90° → Scan L (Orange) [Y total: +270]
5. Y CW 90° → Back to F (White) [Y total: +360 = 0°] ✓

**Phase 2: Scan U, D with X rotation**

6. X fwd 90° → Scan U (Blue) - Wait, X forward brings D to front, not U!

Let me think about X rotation direction:
- X forward (0:B→C, 6:B→A): Cube tumbles toward camera
  - U→F, F→D, D→B, B→U
  - So U (Blue) comes to front ✓

7. X fwd 90° from F=White, U=Blue:
   - U→F: Blue comes to front
   - Scan U (Blue) ✓

8. X back 90° → back to White front
   - F→U, U→B, B→D, D→F
   - Wait, that would put Blue on top of back, not return to start.

Actually after scanning Blue (which is now in front):
- Current: F=Blue, U=White (because U→F means old U is now F, old F went to D)

Let me re-trace:
- Start Phase 2: F=White, U=Blue, D=Green, B=Yellow
- X fwd 90°: U→F, F→D, D→B, B→U
  - F=Blue, U=Yellow, D=White, B=Green
- Scan F (which is Blue = original U face) ✓

Now to scan D (Green, now at B):
- X fwd 90° again: U→F, F→D, D→B, B→U
  - Before: F=Blue, U=Yellow, D=White, B=Green
  - After: F=Yellow, U=Green, D=Blue, B=White
- Scan F (which is Yellow = original B face) - WRONG! We already scanned B.

This is getting confusing. Let me try X backward instead:

- Start Phase 2: F=White, U=Blue, D=Green, B=Yellow
- X back 90°: B→U, U→F, F→D, D→B
  - F=Blue, U=Yellow, D=White, B=Green
  
Same result. The issue is direction naming.

## Let's just be explicit

**X "tumble forward"** (cube rolls toward camera):
- What was on top comes to front
- What was in front goes to bottom
- 0:B→C, 6:B→A

**Start of Phase 2:** F=White, U=Blue, B=Yellow, D=Green

**X tumble forward 90°:**
- U (Blue) → F
- F (White) → D  
- D (Green) → B
- B (Yellow) → U
- **Result:** F=Blue, U=Yellow, B=Green, D=White

**Scan F = Blue (original top)** ✓

**X tumble forward 180° (from here):**
- F↔B, U↔D
- **Result:** F=Green, U=White, B=Blue, D=Yellow

**Scan F = Green (original bottom)** ✓

**X tumble forward 90° to return:**
- U (White) → F
- F (Green) → D
- D (Yellow) → B
- B (Blue) → U
- **Result:** F=White, U=Blue, B=Yellow, D=Green ✓

**Back to start!**

## Final Sequence

### Phase 1: Y rotations (scan 4 side faces)
1. Scan FRONT (White)
2. Y CW 90° → Scan RIGHT (Red)
3. Y CW 90° → Scan BACK (Yellow)
4. Y CW 90° → Scan LEFT (Orange)
5. Y CW 90° → Return to WHITE front [Y = 360° = 0°]

### Phase 2: X rotations (scan top/bottom)
6. X fwd 90° → Scan TOP (Blue)
7. X fwd 180° → Scan BOTTOM (Green)
8. X fwd 90° → Return to WHITE front [X = 360° = 0°]

**Total: Y = 0°, X = 0° → Ends at start!**
