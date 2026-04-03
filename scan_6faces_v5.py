#!/usr/bin/env python3
"""
RCubed 6-Face Scanner V5 - With Full Orientation Tracking

SCAN ORDER:
1. Front (White)
2. Back (Yellow) - Y 180°
3. Right (Red) - Y 90° CW  
4. Left (Orange) - Y 180°
5. Return to White - Y 90° CW
6. Top (Blue) - X forward 90°
7. Bottom (Green) - X forward 180°
8. Return to White/Blue - X forward 90°

COLLISION RULES:
- 0&6 stay at B during Y rotations
- 2&8 stay at B during X rotations
- For photos: 2&8 at A/C (out of camera view)
"""

import sys
import os
import time
import json
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maestro

with open('servo_config.json') as f:
    config = json.load(f)
    GRIPPER = {int(k): v for k, v in config['gripper'].items()}
    RP = {int(k): v for k, v in config['rp'].items()}

GRIPPER_ACCEL = 110
DELAY = 1.5
Y_DELAY = 2.0
X_DELAY = 2.2
X_SPEED = {'0': 60, '6': 45}

SCAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scans')
os.makedirs(SCAN_DIR, exist_ok=True)

CROP_X1, CROP_Y1 = 180, 75
CROP_X2, CROP_Y2 = 460, 400

# ─── Orientation Tracking ───────────────────────────────────────────────────

class CubeOrientation:
    """Track cube orientation throughout scan."""
    
    def __init__(self):
        # Standard orientation: White front, Blue top
        self.F = 'W'  # Front
        self.B = 'Y'  # Back
        self.R = 'R'  # Right
        self.L = 'O'  # Left
        self.U = 'B'  # Up (top)
        self.D = 'G'  # Down (bottom)
    
    def y_cw_90(self):
        """Y axis CW 90° (looking from top): L→F, F→R, R→B, B→L"""
        old_F, old_R, old_B, old_L = self.F, self.R, self.B, self.L
        self.F = old_L
        self.R = old_F
        self.B = old_R
        self.L = old_B
    
    def y_180(self):
        """Y axis 180°: F↔B, R↔L"""
        self.F, self.B = self.B, self.F
        self.R, self.L = self.L, self.R
    
    def x_forward_90(self):
        """X axis forward 90° (tumble toward camera): U→F, F→D, D→B, B→U"""
        old_F, old_U, old_B, old_D = self.F, self.U, self.B, self.D
        self.F = old_U
        self.D = old_F
        self.B = old_D
        self.U = old_B
    
    def x_180(self):
        """X axis 180°: F↔B, U↔D"""
        self.F, self.B = self.B, self.F
        self.U, self.D = self.D, self.U
    
    def __str__(self):
        return f"F={self.F} B={self.B} R={self.R} L={self.L} U={self.U} D={self.D}"
    
    def front(self):
        """Return full color name of front face."""
        names = {'W': 'White', 'Y': 'Yellow', 'R': 'Red', 'O': 'Orange', 'B': 'Blue', 'G': 'Green'}
        return names.get(self.F, self.F)

# Global orientation tracker
cube = CubeOrientation()

# ─── Gripper State ──────────────────────────────────────────────────────────

gripper_state = {0: 'B', 2: 'C', 6: 'B', 8: 'A'}

def wait(t=DELAY):
    time.sleep(t)

def set_gripper(ch, pos, ctrl):
    ctrl.setTarget(ch, GRIPPER[ch][pos] * 4)
    gripper_state[ch] = pos

def set_rp(ch, pos, ctrl):
    ctrl.setTarget(ch, RP[ch][pos] * 4)

def take_photo(name, num, cam):
    ret, frame = cam.read()
    if not ret:
        print(f"  ❌ Failed: {name}")
        return None
    cropped = frame[CROP_Y1:CROP_Y2, CROP_X1:CROP_X2]
    if name == "top":
        cropped = cv2.rotate(cropped, cv2.ROTATE_90_CLOCKWISE)
    elif name == "bottom":
        cropped = cv2.rotate(cropped, cv2.ROTATE_90_COUNTERCLOCKWISE)
    path = os.path.join(SCAN_DIR, f"face_{num}_{name}.jpg")
    cv2.imwrite(path, cropped)
    print(f"  📸 {name} (seeing {cube.front()} face)")
    return path

def y_setup(ctrl):
    """RP 3&9 hold, RP 1&7 retracted for Y rotation"""
    ctrl.setSpeed(3, 50)
    ctrl.setSpeed(9, 50)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    wait()
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    set_rp(1, "retracted", ctrl)
    set_rp(7, "retracted", ctrl)
    wait()

def y_180(ctrl):
    """Y 180°: swap 2&8 positions (A↔C)"""
    print(f"  Y 180° | Before: {cube}")
    if gripper_state[2] == 'C':
        set_gripper(2, 'A', ctrl)
        set_gripper(8, 'C', ctrl)
    else:
        set_gripper(2, 'C', ctrl)
        set_gripper(8, 'A', ctrl)
    wait(Y_DELAY)
    cube.y_180()
    print(f"         | After:  {cube}")

def y_90_cw(ctrl):
    """Y 90° CW: requires reset to B first, then rotate to A/C"""
    print(f"  Y 90° CW | Before: {cube}")
    # Reset 2&8 to B (transfer hold first)
    ctrl.setSpeed(1, 50)
    ctrl.setSpeed(7, 50)
    set_rp(1, "hold", ctrl)
    set_rp(7, "hold", ctrl)
    wait()
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    wait()
    set_gripper(2, 'B', ctrl)
    set_gripper(8, 'B', ctrl)
    wait()
    # Transfer back
    ctrl.setSpeed(3, 50)
    ctrl.setSpeed(9, 50)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    wait()
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    set_rp(1, "retracted", ctrl)
    set_rp(7, "retracted", ctrl)
    wait()
    # Rotate 90° CW: 2:B→A, 8:B→C
    set_gripper(2, 'A', ctrl)
    set_gripper(8, 'C', ctrl)
    wait(Y_DELAY)
    cube.y_cw_90()
    print(f"           | After:  {cube}")

def x_setup(ctrl):
    """RP 1&7 hold, RP 3&9 retracted, 2&8 at B for X rotation"""
    # Move 2&8 to B first
    ctrl.setSpeed(1, 50)
    ctrl.setSpeed(7, 50)
    set_rp(1, "hold", ctrl)
    set_rp(7, "hold", ctrl)
    wait()
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    wait()
    set_gripper(2, 'B', ctrl)
    set_gripper(8, 'B', ctrl)
    wait()

def x_90(ctrl):
    """X forward 90°"""
    print(f"  X fwd 90° | Before: {cube}")
    ctrl.setSpeed(0, X_SPEED['0'])
    ctrl.setSpeed(6, X_SPEED['6'])
    set_gripper(0, 'C', ctrl)
    set_gripper(6, 'A', ctrl)
    time.sleep(X_DELAY)
    ctrl.setSpeed(0, 0)
    ctrl.setSpeed(6, 0)
    # Square cube
    ctrl.setSpeed(3, 50)
    ctrl.setSpeed(9, 50)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    wait()
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    wait()
    # Reset 0&6 to B
    ctrl.setSpeed(3, 50)
    ctrl.setSpeed(9, 50)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    wait()
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    set_rp(1, "retracted", ctrl)
    set_rp(7, "retracted", ctrl)
    wait()
    set_gripper(0, 'B', ctrl)
    set_gripper(6, 'B', ctrl)
    wait()
    ctrl.setSpeed(1, 50)
    ctrl.setSpeed(7, 50)
    set_rp(1, "hold", ctrl)
    set_rp(7, "hold", ctrl)
    wait()
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    wait()
    cube.x_forward_90()
    print(f"            | After:  {cube}")

def prep_photo_after_x(ctrl):
    """After X rotation, move 2&8 to A/C for photo"""
    ctrl.setSpeed(3, 50)
    ctrl.setSpeed(9, 50)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    wait()
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    set_rp(1, "retracted", ctrl)
    set_rp(7, "retracted", ctrl)
    wait()
    set_gripper(2, 'A', ctrl)
    set_gripper(8, 'C', ctrl)
    wait()

def scan_cube(ctrl, cam):
    global cube
    cube = CubeOrientation()  # Reset orientation
    faces = []
    
    print("\n═══ SETUP ═══")
    print(f"  Starting orientation: {cube}")
    
    for ch in [0, 2, 6, 8]:
        ctrl.setAccel(ch, GRIPPER_ACCEL)
    
    set_gripper(0, 'B', ctrl)
    set_gripper(6, 'B', ctrl)
    set_gripper(2, 'C', ctrl)
    set_gripper(8, 'A', ctrl)
    
    for ch in [1, 3, 7, 9]:
        ctrl.setSpeed(ch, 0)
        set_rp(ch, "retracted", ctrl)
    wait()
    
    input("  ⏳ Insert cube (White front, Blue top), press Enter...")
    
    print("  Engaging...")
    for ch in [1, 3, 7, 9]:
        ctrl.setSpeed(ch, 50)
        set_rp(ch, "hold", ctrl)
    wait()
    
    # ═══ PHASE 1: Side faces ═══
    print("\n═══ PHASE 1: Side faces ═══")
    y_setup(ctrl)
    
    print(f"\n[1] FRONT - expecting White")
    f = take_photo("front", 1, cam)
    if f: faces.append(f)
    
    print(f"\n[2] BACK - expecting Yellow")
    y_180(ctrl)
    f = take_photo("back", 2, cam)
    if f: faces.append(f)
    
    print(f"\n[3] RIGHT - expecting Red")
    y_90_cw(ctrl)
    f = take_photo("right", 3, cam)
    if f: faces.append(f)
    
    print(f"\n[4] LEFT - expecting Orange")
    y_180(ctrl)
    f = take_photo("left", 4, cam)
    if f: faces.append(f)
    
    print(f"\n[*] Return to White front")
    y_90_cw(ctrl)
    print(f"  Current orientation: {cube}")
    
    # ═══ PHASE 2: Top/Bottom ═══
    print("\n═══ PHASE 2: Top/Bottom ═══")
    x_setup(ctrl)
    
    print(f"\n[5] TOP - expecting Blue")
    x_90(ctrl)
    prep_photo_after_x(ctrl)
    f = take_photo("top", 5, cam)
    if f: faces.append(f)
    
    print(f"\n[6] BOTTOM - expecting Green")
    # Move 2&8 back to B for X rotation
    ctrl.setSpeed(1, 50)
    ctrl.setSpeed(7, 50)
    set_rp(1, "hold", ctrl)
    set_rp(7, "hold", ctrl)
    wait()
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    wait()
    set_gripper(2, 'B', ctrl)
    set_gripper(8, 'B', ctrl)
    wait()
    
    x_90(ctrl)  # 90°
    x_90(ctrl)  # 180° total
    prep_photo_after_x(ctrl)
    f = take_photo("bottom", 6, cam)
    if f: faces.append(f)
    
    print(f"\n[*] Return to White front, Blue top")
    ctrl.setSpeed(1, 50)
    ctrl.setSpeed(7, 50)
    set_rp(1, "hold", ctrl)
    set_rp(7, "hold", ctrl)
    wait()
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    wait()
    set_gripper(2, 'B', ctrl)
    set_gripper(8, 'B', ctrl)
    wait()
    x_90(ctrl)
    
    print(f"\n═══ DONE: {len(faces)}/6 faces ═══")
    print(f"  Final orientation: {cube}")
    return faces

def reset(ctrl):
    print("\n═══ RESET ═══")
    ctrl.setSpeed(1, 50)
    ctrl.setSpeed(7, 50)
    set_rp(1, "hold", ctrl)
    set_rp(7, "hold", ctrl)
    wait()
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    wait()
    for g in [0, 2, 6, 8]:
        set_gripper(g, 'B', ctrl)
    wait()
    print("  ✅ Done")

def main():
    print("Connecting...")
    ctrl = maestro.Controller('/dev/ttyACM0')
    
    print("Opening camera...")
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("❌ Camera failed")
        ctrl.close()
        return
    print("✅ Ready")
    
    try:
        scan_cube(ctrl, cam)
        reset(ctrl)
    finally:
        cam.release()
        ctrl.close()
    
    print("\nDone!")

if __name__ == '__main__':
    main()
