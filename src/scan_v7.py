#!/usr/bin/env python3
"""
RCubed 6-Face Scanner v7 - Clean Implementation
Based on verified rotation rules (2026-03-31)

Scan order (5 rotations):
1. Front (White)
2. Y 180° → Back (Yellow)
3. Y 90° CW → Right (Red)
4. Y 180° → Left (Orange)
5. X 90° fwd → Top (Blue)
6. X 180° → Bottom (Green)

Verified rotation rules:
- Y 180°: 2:C↔A, 8:A↔C → F↔B, R↔L
- Y 90° CW: 2:B→A, 8:B→C → L→F→R→B→L
- X 90° fwd: 0:B→C, 6:B→A → U→F→D→B→U
"""

import sys
import os
import time
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maestro
import robot_state

# ─── Config ─────────────────────────────────────────────────────────────────

GRIPPER = {
    0: {"A": 400, "B": 1100, "C": 1785, "D": 2420},
    2: {"A": 400, "B": 1040, "C": 1710, "D": 2400},
    6: {"A": 475, "B": 1120, "C": 1800, "D": 2425},
    8: {"A": 450, "B": 1120, "C": 1810, "D": 2425},
}
RP = {
    1: {"retracted": 1890, "hold": 1055},
    3: {"retracted": 1815, "hold": 1100},
    7: {"retracted": 1875, "hold": 990},
    9: {"retracted": 1880, "hold": 1100},
}

X_SPEED = {0: 60, 6: 45}
CROP = (180, 75, 460, 400)
SCAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scans")

# ─── Cube Orientation Tracker ───────────────────────────────────────────────

class Cube:
    """Track cube orientation. Verified 2026-03-31."""
    def __init__(self):
        self.F, self.B = 'W', 'Y'
        self.R, self.L = 'R', 'O'
        self.U, self.D = 'B', 'G'
    
    def y_180(self):
        self.F, self.B = self.B, self.F
        self.R, self.L = self.L, self.R
    
    def y_cw(self):
        self.F, self.R, self.B, self.L = self.L, self.F, self.R, self.B
    
    def y_ccw(self):
        self.F, self.L, self.B, self.R = self.R, self.F, self.L, self.B
    
    def x_fwd(self):
        # U→F, F→D, D→B, B→U
        self.F, self.D, self.B, self.U = self.U, self.F, self.D, self.B
    
    def x_back(self):
        self.F, self.U, self.B, self.D = self.D, self.F, self.U, self.B
    
    def name(self, c):
        return {'W':'White','Y':'Yellow','R':'Red','O':'Orange','B':'Blue','G':'Green'}[c]
    
    def __str__(self):
        return f"F={self.F} B={self.B} U={self.U} D={self.D} R={self.R} L={self.L}"

# ─── Helpers ────────────────────────────────────────────────────────────────

grip = {0: 'B', 2: 'C', 6: 'B', 8: 'A'}  # Track gripper positions

def set_g(ch, pos, ctrl):
    ctrl.setTarget(ch, GRIPPER[ch][pos] * 4)
    grip[ch] = pos

def set_rp(ch, pos, ctrl):
    ctrl.setTarget(ch, RP[ch][pos] * 4)

def wait(t=1.0):
    time.sleep(t)

def photo(name, num, cam, rotation=None):
    """Take photo, apply rotation if needed."""
    time.sleep(0.3)
    for _ in range(3):
        cam.read()
    ret, frame = cam.read()
    if not ret:
        print(f"  ❌ Photo failed: {name}")
        return None
    x1, y1, x2, y2 = CROP
    img = frame[y1:y2, x1:x2]
    if rotation == 'CW90':
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    elif rotation == 'CCW90':
        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    path = os.path.join(SCAN_DIR, f"face_{num}_{name}.jpg")
    cv2.imwrite(path, img)
    return path

# ─── Rotation Primitives ────────────────────────────────────────────────────

def y_180(ctrl, cube):
    """Y 180°: 2:C↔A, 8:A↔C"""
    print("  Y 180°")
    if grip[2] == 'C':
        set_g(2, 'A', ctrl)
        set_g(8, 'C', ctrl)
    else:
        set_g(2, 'C', ctrl)
        set_g(8, 'A', ctrl)
    wait(2.0)
    cube.y_180()

def y_90_cw(ctrl, cube):
    """Y 90° CW: reset to B, then 2:B→A, 8:B→C"""
    print("  Y 90° CW")
    # Transfer hold to 0&6 - wait for solid grip before releasing 3&9
    ctrl.setSpeed(1, 30)
    ctrl.setSpeed(7, 30)
    set_rp(1, "hold", ctrl)
    set_rp(7, "hold", ctrl)
    wait(2.0)  # Longer wait for solid grip
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    wait(2.0)
    # Reset 2&8 to B
    set_g(2, 'B', ctrl)
    set_g(8, 'B', ctrl)
    wait()
    # Transfer back to 2&8
    ctrl.setSpeed(3, 30)
    ctrl.setSpeed(9, 30)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    wait(2.0)  # Wait for solid grip
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    set_rp(1, "retracted", ctrl)
    set_rp(7, "retracted", ctrl)
    wait(2.0)
    # Rotate
    set_g(2, 'A', ctrl)
    set_g(8, 'C', ctrl)
    wait(2.0)
    cube.y_cw()

def y_90_ccw(ctrl, cube):
    """Y 90° CCW: reset to B, then 2:B→C, 8:B→A"""
    print("  Y 90° CCW")
    # Transfer hold to 0&6 - wait for solid grip before releasing 3&9
    ctrl.setSpeed(1, 30)
    ctrl.setSpeed(7, 30)
    set_rp(1, "hold", ctrl)
    set_rp(7, "hold", ctrl)
    wait(2.0)
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    wait(2.0)
    # Reset 2&8 to B
    set_g(2, 'B', ctrl)
    set_g(8, 'B', ctrl)
    wait()
    # Transfer back to 2&8
    ctrl.setSpeed(3, 30)
    ctrl.setSpeed(9, 30)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    wait(2.0)
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    set_rp(1, "retracted", ctrl)
    set_rp(7, "retracted", ctrl)
    wait(2.0)
    # Rotate CCW: 2:B→C, 8:B→A
    set_g(2, 'C', ctrl)
    set_g(8, 'A', ctrl)
    wait(2.0)
    cube.y_ccw()

def x_setup(ctrl):
    """Setup for X rotation: 1&7 hold, 3&9 retracted, 2&8 at B"""
    print("  X setup")
    ctrl.setSpeed(1, 30)
    ctrl.setSpeed(7, 30)
    set_rp(1, "hold", ctrl)
    set_rp(7, "hold", ctrl)
    wait(2.0)  # Longer wait for solid grip
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    wait(2.0)
    set_g(2, 'B', ctrl)
    set_g(8, 'B', ctrl)
    wait()

def x_90_fwd(ctrl, cube):
    """X 90° forward: 0:B→C, 6:B→A"""
    print("  X 90° fwd")
    ctrl.setSpeed(0, X_SPEED[0])
    ctrl.setSpeed(6, X_SPEED[6])
    set_g(0, 'C', ctrl)
    set_g(6, 'A', ctrl)
    wait(2.5)
    ctrl.setSpeed(0, 0)
    ctrl.setSpeed(6, 0)
    cube.x_fwd()

def x_180_fwd(ctrl, cube):
    """X 180° forward: two X 90° moves with minimal reset between"""
    print("  X 180° fwd (two 90° moves)")
    
    # First 90°: 0:B→C, 6:B→A
    ctrl.setSpeed(0, X_SPEED[0])
    ctrl.setSpeed(6, X_SPEED[6])
    set_g(0, 'C', ctrl)
    set_g(6, 'A', ctrl)
    wait(2.5)
    ctrl.setSpeed(0, 0)
    ctrl.setSpeed(6, 0)
    cube.x_fwd()
    
    # Quick grip transfer: 3&9 hold, 1&7 release, reset 0&6 to B
    ctrl.setSpeed(3, 30)
    ctrl.setSpeed(9, 30)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    wait(2.0)
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    set_rp(1, "retracted", ctrl)
    set_rp(7, "retracted", ctrl)
    wait(2.0)
    set_g(0, 'B', ctrl)
    set_g(6, 'B', ctrl)
    wait(1.0)
    # Transfer back: 1&7 hold, 3&9 release
    ctrl.setSpeed(1, 30)
    ctrl.setSpeed(7, 30)
    set_rp(1, "hold", ctrl)
    set_rp(7, "hold", ctrl)
    wait(2.0)
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    wait(2.0)
    
    # Second 90°: 0:B→C, 6:B→A
    ctrl.setSpeed(0, X_SPEED[0])
    ctrl.setSpeed(6, X_SPEED[6])
    set_g(0, 'C', ctrl)
    set_g(6, 'A', ctrl)
    wait(2.5)
    ctrl.setSpeed(0, 0)
    ctrl.setSpeed(6, 0)
    cube.x_fwd()

def x_reset(ctrl):
    """Reset 0&6 to B after X rotation"""
    print("  X reset")
    # Square cube
    ctrl.setSpeed(3, 30)
    ctrl.setSpeed(9, 30)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    wait(1.5)
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    wait(2.0)
    # Transfer to 2&8 - wait for solid grip
    ctrl.setSpeed(3, 30)
    ctrl.setSpeed(9, 30)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    wait(2.0)  # Longer wait for solid grip
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    set_rp(1, "retracted", ctrl)
    set_rp(7, "retracted", ctrl)
    wait(2.0)
    # Reset 0&6
    set_g(0, 'B', ctrl)
    set_g(6, 'B', ctrl)
    wait(1.0)
    # Transfer back - wait for solid grip
    ctrl.setSpeed(1, 30)
    ctrl.setSpeed(7, 30)
    set_rp(1, "hold", ctrl)
    set_rp(7, "hold", ctrl)
    wait(2.0)  # Longer wait for solid grip
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    wait(2.0)

# ─── Main Scan ──────────────────────────────────────────────────────────────

def scan(ctrl, cam):
    os.makedirs(SCAN_DIR, exist_ok=True)
    cube = Cube()
    faces = []
    
    # Setup: set acceleration
    for ch in [0, 2, 6, 8]:
        ctrl.setAccel(ch, 110)
    
    # Engage all
    print("\n═══ ENGAGING ═══")
    for ch in [1, 3, 7, 9]:
        ctrl.setSpeed(ch, 30)
        set_rp(ch, "hold", ctrl)
    wait(1.5)
    
    # Setup for Y rotations: 3&9 hold, 1&7 retracted
    print("\n═══ Y SETUP ═══")
    ctrl.setSpeed(3, 30)
    ctrl.setSpeed(9, 30)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    wait()
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    set_rp(1, "retracted", ctrl)
    set_rp(7, "retracted", ctrl)
    wait(1.5)
    
    # 1. Front
    print(f"\n[1/6] FRONT ({cube.name(cube.F)})")
    f = photo("front", 1, cam)
    if f: faces.append(f)
    
    # 2. Y 180° → Back
    print(f"\n[2/6] BACK")
    y_180(ctrl, cube)
    print(f"  Now: {cube.name(cube.F)}")
    f = photo("back", 2, cam)
    if f: faces.append(f)
    
    # 3. Y 90° CW → Right
    print(f"\n[3/6] RIGHT")
    y_90_cw(ctrl, cube)
    print(f"  Now: {cube.name(cube.F)}")
    f = photo("right", 3, cam)
    if f: faces.append(f)
    
    # 4. Y 180° → Left
    print(f"\n[4/6] LEFT")
    y_180(ctrl, cube)
    print(f"  Now: {cube.name(cube.F)}")
    f = photo("left", 4, cam)
    if f: faces.append(f)
    
    # 5. Return to White front before X rotations
    print(f"\n[*] RETURN TO WHITE FRONT")
    y_90_ccw(ctrl, cube)
    print(f"  Now: {cube.name(cube.F)}")
    
    # 6. X 90° fwd → Top
    print(f"\n[5/6] TOP")
    x_setup(ctrl)
    x_90_fwd(ctrl, cube)
    print(f"  Now: {cube.name(cube.F)}")
    f = photo("top", 5, cam, 'CW90')
    if f: faces.append(f)
    
    # 7. X 180° fwd → Bottom
    print(f"\n[6/6] BOTTOM")
    x_reset(ctrl)
    x_setup(ctrl)
    x_180_fwd(ctrl, cube)
    print(f"  Now: {cube.name(cube.F)}")
    f = photo("bottom", 6, cam, 'CCW90')
    if f: faces.append(f)
    
    # Return to White front: after final reset, cube will be at Yellow front
    # Need one X forward to get to White
    print(f"\n[*] RETURN TO WHITE FRONT")
    x_reset(ctrl)  # Green → Yellow (moves 0&6 to B)
    x_setup(ctrl)
    x_90_fwd(ctrl, cube)  # Yellow → White
    print(f"  Now: {cube.name(cube.F)} front")
    
    print(f"\n═══ DONE: {len(faces)}/6 ═══")
    print(f"Final orientation: {cube}")
    for f in faces:
        print(f"  {f}")
    
    return cube

def main():
    print("Connecting...")
    ctrl = maestro.Controller('/dev/ttyACM0')
    
    print("Opening camera...")
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("❌ Camera failed")
        ctrl.close()
        return
    
    try:
        cube = scan(ctrl, cam)
        print("\n═══ RESET ═══")
        # After return sequence: 0&6 at C/A, 1&7 holding, 3&9 retracted, 2&8 at B
        # Engage 3&9 — now all 4 RPs hold, ready for solve
        ctrl.setSpeed(3, 30)
        ctrl.setSpeed(9, 30)
        set_rp(3, "hold", ctrl)
        set_rp(9, "hold", ctrl)
        wait(1.5)
        print("Done - cube held, ready for solve")

        # Save state: grip dict tracks final gripper positions, all RPs now holding
        robot_state.save(
            gripper_pos=dict(grip),
            rp_status={1: 'hold', 3: 'hold', 7: 'hold', 9: 'hold'},
        )

    except KeyboardInterrupt:
        print("\n⚠️ Interrupted")
        robot_state.invalidate()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        robot_state.invalidate()
        raise
    finally:
        cam.release()
        ctrl.close()

if __name__ == '__main__':
    main()
