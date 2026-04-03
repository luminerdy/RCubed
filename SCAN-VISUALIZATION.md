# Scan Choreography - What Gets Scanned

## Starting Position (Load)
```
     [BLUE]
[ORANGE] [WHITE] [RED]
     [GREEN]
      [YELLOW]
```
**You loaded:** White front, Blue top
- Front = White, Back = Yellow
- Right = Red, Left = Orange  
- Top = Blue, Bottom = Green

---

## STEP 3: Scan FRONT
**Cube orientation:** White front, Blue top
```
📸 Scanning FRONT face
     [BLUE]
[ORANGE] [WHITE] [RED]
     [GREEN]
```
**Scanned image:** face_1_front.jpg = WHITE center

---

## STEP 4-5: Y 180° rotation → Scan BACK
**Gripper 2: C→A, Gripper 8: A→C** (opposite = 180° Y)

After rotation: Front ↔ Back, Right ↔ Left
```
📸 Scanning BACK (was front)
     [BLUE]
  [RED] [YELLOW] [ORANGE]
     [GREEN]
```
**Scanned image:** face_2_back.jpg = YELLOW center (was back, stayed back)

**WAIT - This is wrong!** After 180° Y:
- What was front (White) → now back
- What was back (Yellow) → now front
- Camera sees YELLOW, not White!

So face_2_back.jpg should have YELLOW center, but we're calling it "back" scan.

Let me trace this correctly...

---

## Actually, let me trace what the CAMERA sees:

### STEP 3: Camera sees FRONT
- Physical cube: White facing camera
- **face_1_front.jpg = WHITE center ✓**

### STEP 4-5: Y 180° → Camera sees what WAS the BACK
- After Y 180°: Yellow now faces camera
- **face_2_back.jpg = YELLOW center ✓**
- (We're scanning "back" but it's physically the front now)

### STEP 6: Y CW 90° → Camera sees what WAS the RIGHT
- From STEP 5 position (Yellow front)
- Y CW 90°: Yellow→Right, Right(Orange)→Back, Back(White)→Left, Left(Red)→Front
- **face_3_right.jpg = RED center** (was front originally)

### STEP 8-9: Y 180° → Camera sees what WAS the LEFT  
- From STEP 7: Red front
- Y 180°: Red↔Orange (front↔back)
- **face_4_left.jpg = ORANGE center ✓**

### STEP 10-11: X forward 90° → Camera sees what WAS the BOTTOM
- From STEP 9: Orange front, Blue top
- X forward: Orange→Top, Blue→Back, Green(was bottom)→Front
- **face_5_top.jpg = GREEN center** (was bottom!)

### STEP 12-13: X 180° → Camera sees what WAS the TOP
- From STEP 11: Green front, Orange top
- X 180°: Green↔Orange (front↔back), Orange↔Green (top↔bottom)
- Wait, that doesn't work either...

---

## The Problem

The scan file NAMES don't match the ACTUAL face centers being scanned!

**Let me check what SHOULD be in each file based on load orientation:**

Starting: F=White, B=Yellow, R=Red, L=Orange, U=Blue, D=Green

What should each scan contain:
- face_1_**front**.jpg → WHITE center (scanning F) ✓
- face_2_**back**.jpg → YELLOW center (scanning B) ✓  
- face_3_**right**.jpg → RED center (scanning R) ✓
- face_4_**left**.jpg → ORANGE center (scanning L) ✓
- face_5_**top**.jpg → BLUE center (scanning U) ✓
- face_6_**bottom**.jpg → GREEN center (scanning D) ✓

Can you check the actual scan images and tell me what color centers are in each file? That will tell us where the choreography is going wrong.
