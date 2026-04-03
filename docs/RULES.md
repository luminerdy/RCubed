# RCubed Rules & Mechanics Reference

## Physical Layout

```
        Camera
           ↓
    ┌─────────────┐
    │   Gripper 2 │  (top, servo 2, RP 3)
    │      ↓      │
    │  0 → □ ← 6  │  Gripper 0 (left), Gripper 6 (right)
    │      ↑      │
    │   Gripper 8 │  (bottom, servo 8, RP 9)
    └─────────────┘
```

- **Gripper servos (even):** 0=left, 2=top, 6=right, 8=bottom
- **RP servos (odd):** 1=left, 3=top, 7=right, 9=bottom
- **Channels 4&5:** Skipped
- **Camera:** Front-facing, sees the face between all 4 grippers

## Cube Orientation (Standard)

```
        Blue (U)
           ↑
Orange (L) ← White (F) → Red (R)
           ↓
        Green (D)
        
    Yellow (B) = behind
```

**Centers:** F=White, B=Yellow, R=Red, L=Orange, U=Blue, D=Green

---

## Servo Positions

### Gripper Servos (0, 2, 6, 8)
- **4 positions:** A, B, C, D (each ~90° apart)
- **Neutral/Start:** B
- **Direction:** A→B→C→D = **CW from the face's perspective** (looking at the face the gripper controls)

| Servo | A (μs) | B (μs) | C (μs) | D (μs) |
|-------|--------|--------|--------|--------|
| 0     | 400    | 1100   | 1785   | 2420   |
| 2     | 400    | 1040   | 1710   | 2400   |
| 6     | 475    | 1120   | 1800   | 2425   |
| 8     | 450    | 1120   | 1810   | 2425   |

### RP Servos (1, 3, 7, 9)
- **2 positions:** retracted, hold
- **Start:** retracted

| Servo | Retracted (μs) | Hold (μs) |
|-------|----------------|-----------|
| 1     | 1890           | 1055      |
| 3     | 1815           | 1100      |
| 7     | 1875           | 990       |
| 9     | 1880           | 1100      |

---

## Face Turns (Single Face Rotation)

When a gripper turns, it rotates the face it's holding.

**VERIFIED 2026-03-06:** All servos follow the same pattern:

| Gripper | Controls | CW Turn | CCW Turn | 180° Turn |
|---------|----------|---------|----------|-----------|
| 0       | L face   | B→C     | B→A      | B→D       |
| 2       | U face   | B→C     | B→A      | B→D       |
| 6       | R face   | B→C     | B→A      | B→D       |
| 8       | D face   | B→C     | B→A      | B→D       |

**Process:**
1. All 4 RP servos hold
2. Gripper rotates (B→C for CW, etc.)
3. Retract the turning gripper's RP
4. Reset gripper to B
5. Re-engage RP

---

## Whole Cube Rotations

### Y Rotation (Spin around vertical axis, U/D stay in place)
**Grippers 2&8 rotate, 0&6 must be clear**

| Action | Servo 2 | Servo 8 | Cube Result |
|--------|---------|---------|-------------|
| Y 90° CW (looking from top) | B→A | B→C | L→F, F→R, R→B, B→L |
| Y 90° CCW | B→C | B→A | R→F, F→L, L→B, B→R |
| Y 180° | A↔C | A↔C | F↔B, R↔L |

**RP during Y rotation:**
- RP 3&9: HOLD (grippers 2&8 control cube)
- RP 1&7: RETRACTED (grippers 0&6 out of the way)

### X Rotation (Tumble forward/backward, R/L stay in place)
**Grippers 0&6 rotate, 2&8 must be clear**

| Action | Servo 0 | Servo 6 | Cube Result |
|--------|---------|---------|-------------|
| X 90° forward (top falls toward camera) | B→C | B→A | U→F, F→D, D→B, B→U |
| X 90° backward | B→A | B→C | D→F, F→U, U→B, B→D |
| X 180° | A↔C | A↔C | F↔B, U↔D |

**RP during X rotation:**
- RP 1&7: HOLD (grippers 0&6 control cube)
- RP 3&9: RETRACTED (grippers 2&8 out of the way)

**X Rotation Speeds (synchronized):**
- Servo 0: speed=60 (slower)
- Servo 6: speed=45 (faster to match)

---

## Collision Rules

### Adjacent Gripper Pairs
- 0&2 (left & top)
- 0&8 (left & bottom)
- 6&2 (right & top)
- 6&8 (right & bottom)

### Safe Combinations
- All grippers at B or D: **SAFE**
- 0&6 at B, 2&8 at A/C: **SAFE** (for Y rotation)
- 0&6 at A/C, 2&8 at B: **SAFE** (for X rotation)

### COLLISION (Avoid!)
- Adjacent grippers BOTH at A: **COLLISION**
- Adjacent grippers BOTH at C: **COLLISION**
- One at A, adjacent at C: **Check clearance**

---

## Camera View

### Gripper Finger Visibility
- **B and D:** Fingers IN camera view (blocking)
- **A and C:** Fingers OUT of camera view (clear)

### For Scanning Side Faces (F, B, R, L)
- Grippers 2&8 at A/C (out of view)
- Grippers 0&6 at B (doesn't matter, they're on sides)

### For Scanning Top/Bottom (U, D)
- After X rotation, grippers 0&6 are at A/C (clear)
- Grippers 2&8 should be at B (clear for top/bottom view)

---

## Timing Constants

| Action | Delay |
|--------|-------|
| General move | 0.8s |
| Slow RP engage | 1.5s |
| RP retract | 2.0s |
| 90° turn | 1.2s |
| 180° turn | 2.0s |
| X rotation | 2.2s |
| Photo settle | 0.5s |

---

## Scan Sequence (Original Working)

### Starting Positions
- Gripper 0: B
- Gripper 2: C (out of camera view)
- Gripper 6: B
- Gripper 8: A (out of camera view)
- All RP: retracted

### Sequence
1. **Front** - Photo (2&8 at C/A = clear)
2. **Y 180°** (2:C→A, 8:A→C) → **Back** - Photo
3. **Y 90°** (reset 2&8 to B, then 2:B→A, 8:B→C) → **Right** - Photo
4. **Y 180°** (2:A→C, 8:C→A) → **Left** - Photo
5. **Prep X:** Engage 1&7, retract 3&9, move 2&8 to B
6. **X 90°** (0:B→C, 6:B→A) → **Top** - Photo
7. **X 180°** (0:C→A, 6:A→C) → **Bottom** - Photo

### After Scan
- Cube orientation: NOT at White/Blue
- Manual reorientation or calculated return needed

---

## Verified 2026-03-31 ✅

All rotation rules tested with physical cube and camera verification.

| Rotation | Servo Moves | Effect | Test |
|----------|-------------|--------|------|
| Y 180° | 2:C↔A, 8:A↔C | F↔B, R↔L | White→Yellow ✅ |
| Y 90° CW | 2:B→A, 8:B→C | L→F→R→B→L | Yellow→Red ✅ |
| Y 90° CCW | 2:B→C, 8:B→A | R→F→L→B→R | Red→Yellow ✅ |
| X 90° fwd | 0:B→C, 6:B→A | U→F→D→B→U | Yellow→Blue ✅ |
| X 90° back | 0:B→A, 6:B→C | D→F→U→B→D | White→Green ✅ |

---

## Working Scan Sequence (scan_v7.py) - Verified 2026-03-31

1. **Front** (White) - photo
2. **Y 180°** → Back (Yellow) - photo
3. **Y 90° CW** → Right (Red) - photo
4. **Y 180°** → Left (Orange) - photo
5. **Y 90° CCW** → Return to White front
6. **X 90° fwd** → Top (Blue) - photo [rotate CW90]
7. **X 180° fwd** (two 90° moves) → Bottom (Green) - photo [rotate CCW90]
8. **X 90° fwd** → Return to White front, Blue top
9. **Engage 3&9** → All 4 RPs holding, ready for solve

## Image Rotations for Kociemba

| Face | Rotation |
|------|----------|
| Front (White) | None |
| Back (Yellow) | None |
| Right (Red) | None |
| Left (Orange) | None |
| Top (Blue) | CW 90° |
| Bottom (Green) | CCW 90° |
