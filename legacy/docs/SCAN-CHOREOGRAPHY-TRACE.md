# Scan Choreography Trace

## Initial State (Load Position)
- F=White, B=Yellow, R=Red, L=Orange, U=Blue, D=Green
- Grippers: 0&6=B, 2=C, 8=A
- RP: all retracted

## Step 1-2: Engage grippers
- RP 1,3,7,9 → hold
- RP 1&7 → retracted
- State: F=White, B=Yellow, R=Red, L=Orange, U=Blue, D=Green

## Step 3: Scan FRONT (White)
- State: F=White, B=Yellow, R=Red, L=Orange, U=Blue, D=Green

## Step 4-5: 180° Y rotation + Scan BACK
- Grippers 2&8: C→A, A→C (opposite directions = 180° Y)
- After 180° Y: F↔B, R↔L, U stays, D stays
- State: F=Yellow, B=White, R=Orange, L=Red, U=Blue, D=Green
- Scan BACK (White center now on back)

## Step 6: Y CW 90° rotation
- Transfer hold to 1&7, reset 2&8 to B, transfer back to 3&9
- Grippers 2&8: B→A, B→C (opposite = Y CW 90°)
- After Y CW 90°: previous F→R, R→B, B→L, L→F, U stays, D stays
- State: F=Red, R=Yellow, B=Orange, L=White, U=Blue, D=Green

## Step 7: Scan RIGHT
- State: F=Red, R=Yellow (scan this)

## Step 8-9: 180° Y rotation + Scan LEFT
- Grippers 2&8: A→C, C→A (180° Y)
- After 180° Y: F↔B, R↔L
- State: F=Orange, B=Red, R=White, L=Yellow, U=Blue, D=Green
- Scan LEFT (White center now on right, which is physically left)

## Step 10: X forward tumble 90°
- Transfer hold, move 2&8 to B
- Grippers 0&6: B→C, B→A (X forward)
- After X forward: F→U, U→B, B→D, D→F, R stays, L stays
- State: F=Green, U=Orange, B=Blue, D=Red, R=White, L=Yellow

## Step 11: Scan TOP
- State: F=Green, U=Orange (scan this)

## Step 12-13: 180° X tumble + Scan BOTTOM
- Grippers 0&6: C→A, A→C (180° X)
- After 180° X: F↔B, U↔D
- State: F=Blue, B=Green, U=Red, D=Orange, R=White, L=Yellow
- Scan BOTTOM (Orange center now on top, which is physically bottom)

## Step 14 CURRENT: Return attempt
### 14a: X forward tumble
- After X forward: F→U, U→B, B→D, D→F
- State: F=Orange, U=Blue, B=Red, D=Green, R=White, L=Yellow

### 14b: Y CCW rotation  
- After Y CCW: F→L, L→B, B→R, R→F, U stays, D stays
- State: F=White, L=Orange, B=Yellow, R=Red, U=Blue, D=Green

Wait, that should be correct! Let me re-check...

Actually looking at state after Step 13:
F=Blue, B=Green, U=Red, D=Orange, R=White, L=Yellow

After X forward (F→U, U→B, B→D, D→F):
F=Orange, U=Blue, B=Red, D=Green, R=White, L=Yellow

After Y CCW (F→L, L→B, B→R, R→F):
F=White, U=Blue, B=Yellow, R=Red, L=Orange, D=Green

That's correct! But user says it ends at White front, Red top...

Let me check if the rotation directions are wrong.
