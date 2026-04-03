# Debugging Step 14 - Where does the cube end up?

## After Step 13 (before Step 14)
Based on the choreography trace:
- After scanning bottom face at end of Step 13
- **Cube should be:** F=Blue, U=Red, R=White, L=Yellow, B=Green, D=Orange

## Step 14a: X forward tumble (0:B→C, 6:B→A)
F→U, U→B, B→D, D→F
- Before: F=Blue, U=Red, B=Green, D=Orange
- After: F=Orange, U=Blue, B=Red, D=Green
- **State:** F=Orange, U=Blue, R=White, L=Yellow, B=Red, D=Green

## Step 14b: Y CCW rotation (2:B→C, 8:B→A)
F→L, L→B, B→R, R→F
- Before: F=Orange, R=White, B=Red, L=Yellow
- After: F=White, R=Orange, B=Yellow, L=Red
- **State:** F=White, U=Blue, R=Orange, L=Red, B=Yellow, D=Green

Wait, that's not right either! R should be Red, not Orange.

## Step 14c: Y CW rotation (2:B→A, 8:B→C)
F→R, R→B, B→L, L→F
- Before: F=White, R=Orange, B=Yellow, L=Red
- After: F=Red, R=White, B=Orange, L=Yellow
- **State:** F=Red, U=Blue, R=White, L=Yellow, B=Orange, D=Green

But you're seeing: F=Blue, U=Red, L=Yellow

This means Step 14 isn't completing! Let me check if the grippers are actually in opposite positions...

## ACTUAL PROBLEM

When grippers 2 and 8 are commanded:
- Gripper 2: B→C (should be CCW from cube perspective)
- Gripper 8: B→A (should be CW from cube perspective)

But if they're moving in the SAME direction instead of opposite, the cube won't rotate!

Let me check the servo calibration - maybe 2 and 8 have the same CW direction?
