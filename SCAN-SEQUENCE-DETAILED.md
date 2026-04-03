# Complete Scan Sequence - Step by Step

## LOAD POSITION (Starting State)
**You insert cube:**
- Front face (toward camera): White center
- Top face: Blue center
- Right face: Red center
- Left face: Orange center
- Back face: Yellow center
- Bottom face: Green center

**Gripper positions:**
- Grippers 0 & 6 (left/right): B position
- Gripper 2 (top): C position
- Gripper 8 (bottom): A position
- All RP: retracted

---

## SCAN BEGINS

### SETUP
- Move grippers to start: 0→B, 2→C, 6→B, 8→A
- Retract all RP
- **User presses Enter (cube already loaded)**

### STEP 1: Engage all 4 RP
- RP 1,3,7,9 → hold (cube secured from all 4 sides)
- **Cube orientation: F=White, U=Blue, R=Red, L=Orange, B=Yellow, D=Green**

### STEP 2: Retract RP 1&7
- RP 1&7 → retracted (open view for camera)
- **Cube orientation: F=White, U=Blue, R=Red, L=Orange, B=Yellow, D=Green**

### STEP 3: Capture FRONT face
- **📸 Scan face_1_front.jpg (White center)**
- **Cube orientation: F=White, U=Blue, R=Red, L=Orange, B=Yellow, D=Green**

### STEP 4: 180° rotation (grippers 2&8)
- Gripper 2: C→A
- Gripper 8: A→C
- **(opposite directions = 180° Y rotation)**
- **After rotation: F↔B, R↔L**
- **Cube orientation: F=Yellow, U=Blue, R=Orange, L=Red, B=White, D=Green**

### STEP 5: Capture BACK face
- **📸 Scan face_2_back.jpg (White center - was on front, now on back)**
- **Cube orientation: F=Yellow, U=Blue, R=Orange, L=Red, B=White, D=Green**

### STEP 6: 90° cube rotation (Y axis)
- Engage RP 1&7
- Retract RP 3&9
- Reset grippers 2&8 to B
- Re-engage RP 3&9
- Retract RP 1&7
- Rotate: 2:B→A, 8:B→C
- **(opposite directions = 90° Y CW rotation)**
- **After rotation: F→R, R→B, B→L, L→F**
- **Cube orientation: F=Red, U=Blue, R=Yellow, L=White, B=Orange, D=Green**

### STEP 7: Capture RIGHT face
- **📸 Scan face_3_right.jpg (Yellow center - was on back, now on right)**
- **Cube orientation: F=Red, U=Blue, R=Yellow, L=White, B=Orange, D=Green**

### STEP 8: 180° rotation (grippers 2&8)
- Gripper 2: A→C
- Gripper 8: C→A
- **(180° Y rotation)**
- **After rotation: F↔B, R↔L**
- **Cube orientation: F=Orange, U=Blue, R=White, L=Yellow, B=Red, D=Green**

### STEP 9: Capture LEFT face
- **📸 Scan face_4_left.jpg (White center - was on right, now on left)**
- **Cube orientation: F=Orange, U=Blue, R=White, L=Yellow, B=Red, D=Green**

### STEP 10: Prep for top/bottom (X tumble)
- Engage RP 1&7
- Retract RP 3&9
- Move grippers 2&8 to B (clear path for 0&6)
- Tumble: 0:B→C, 6:B→A
- **(opposite directions = 90° X forward tumble)**
- **After tumble: F→U, U→B, B→D, D→F**
- **Cube orientation: F=Green, U=Orange, R=White, L=Yellow, B=Blue, D=Red**
- Square cube with RP 3&9
- Retract RP 3&9

### STEP 11: Capture TOP face
- **📸 Scan face_5_top.jpg (Orange center - was on front, now on top)**
- **Cube orientation: F=Green, U=Orange, R=White, L=Yellow, B=Blue, D=Red**

### STEP 12: 180° tumble (grippers 0&6)
- Gripper 0: C→A
- Gripper 6: A→C
- **(180° X tumble)**
- **After tumble: F↔B, U↔D**
- **Cube orientation: F=Blue, U=Red, R=White, L=Yellow, B=Green, D=Orange**
- Square cube with RP 3&9
- Retract RP 3&9

### STEP 13: Capture BOTTOM face
- **📸 Scan face_6_bottom.jpg (Orange center - was on top, now on bottom)**
- **Cube orientation: F=Blue, U=Red, R=White, L=Yellow, B=Green, D=Orange**

---

## STEP 14: Return to original orientation

**Current state:** F=Blue, U=Red, R=White, L=Yellow, B=Green, D=Orange
**Target state:** F=White, U=Blue, R=Red, L=Orange, B=Yellow, D=Green

### 14a: X forward tumble
- Reset grippers 0&6 to B
- Engage RP 1&7
- Retract RP 3&9
- Tumble: 0:B→C, 6:B→A (X forward)
- **After tumble: F→U, U→B, B→D, D→F**
- **Cube orientation: F=Orange, U=Blue, R=White, L=Yellow, B=Red, D=Green**

### 14b: Y CCW rotation
- Engage RP 3&9
- Retract RP 1&7
- Reset grippers 0&6 to B
- Re-engage RP 1&7
- Retract RP 3&9
- Reset grippers 2&8 to B
- Re-engage RP 3&9
- Retract RP 1&7
- Rotate: 2:B→C, 8:B→A (Y CCW)
- **After rotation: F→L, L→B, B→R, R→F**
- **Expected final: F=White, U=Blue, R=Red, L=Orange, B=Yellow, D=Green**

---

## PROBLEM

If you're seeing **Green front, Red top** after the scan, that means:
- Current: F=Green, U=Red
- This matches the state at **STEP 11** (before Step 12)!

**This suggests Step 12-14 aren't executing properly or the cube isn't being held correctly during those steps.**

Let me check if the issue is with cube squaring after X rotations...
