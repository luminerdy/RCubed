#!/usr/bin/env python3
"""
Test rotations and verify cube orientation tracking.
Takes photo, does rotation, takes photo, compares to expected.
"""

import sys
import os
import time
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maestro

# Servo config
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

GRIPPER_ACCEL = 110
X_SPEED = {0: 60, 6: 45}

# Crop bounds
CROP = (180, 75, 460, 400)

# Current gripper positions
grip_pos = {0: 'B', 2: 'C', 6: 'B', 8: 'A'}

def set_g(ch, pos, ctrl):
    ctrl.setTarget(ch, GRIPPER[ch][pos] * 4)
    grip_pos[ch] = pos

def set_rp(ch, pos, ctrl):
    ctrl.setTarget(ch, RP[ch][pos] * 4)

def take_photo(name, cam):
    """Take photo and save it."""
    time.sleep(0.3)
    for _ in range(3):
        cam.read()
    ret, frame = cam.read()
    if ret:
        x1, y1, x2, y2 = CROP
        cropped = frame[y1:y2, x1:x2]
        path = f"/home/luminerdy/rcubed/test_{name}.jpg"
        cv2.imwrite(path, cropped)
        print(f"📸 Saved: {path}")
        return path
    return None

def engage_all(ctrl):
    """Engage all RP servos."""
    for ch in [1, 3, 7, 9]:
        ctrl.setSpeed(ch, 30)
        set_rp(ch, "hold", ctrl)
    time.sleep(1.5)
    for ch in [1, 3, 7, 9]:
        ctrl.setSpeed(ch, 0)

def y_setup(ctrl):
    """Setup for Y rotation: RP 3&9 hold, RP 1&7 retracted."""
    ctrl.setSpeed(3, 30)
    ctrl.setSpeed(9, 30)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    time.sleep(1.0)
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    set_rp(1, "retracted", ctrl)
    set_rp(7, "retracted", ctrl)
    time.sleep(1.5)

def y_reset_to_b(ctrl):
    """Reset grippers 2&8 to B (requires transfer to 0&6 first)."""
    # Transfer hold to 0&6
    ctrl.setSpeed(1, 30)
    ctrl.setSpeed(7, 30)
    set_rp(1, "hold", ctrl)
    set_rp(7, "hold", ctrl)
    time.sleep(1.0)
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    time.sleep(1.5)
    # Reset 2&8 to B
    set_g(2, 'B', ctrl)
    set_g(8, 'B', ctrl)
    time.sleep(1.0)
    # Transfer back
    ctrl.setSpeed(3, 30)
    ctrl.setSpeed(9, 30)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    time.sleep(1.0)
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    set_rp(1, "retracted", ctrl)
    set_rp(7, "retracted", ctrl)
    time.sleep(1.5)

def x_setup(ctrl):
    """Setup for X rotation: RP 1&7 hold, RP 3&9 retracted, 2&8 at B."""
    # Transfer to 0&6
    ctrl.setSpeed(1, 30)
    ctrl.setSpeed(7, 30)
    set_rp(1, "hold", ctrl)
    set_rp(7, "hold", ctrl)
    time.sleep(1.0)
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    time.sleep(1.5)
    # Ensure 2&8 at B
    set_g(2, 'B', ctrl)
    set_g(8, 'B', ctrl)
    time.sleep(1.0)

def x_reset_to_b(ctrl):
    """Reset grippers 0&6 to B after X rotation."""
    # Square cube first
    ctrl.setSpeed(3, 30)
    ctrl.setSpeed(9, 30)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    time.sleep(1.0)
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    time.sleep(1.5)
    # Transfer hold to 2&8
    ctrl.setSpeed(3, 30)
    ctrl.setSpeed(9, 30)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    time.sleep(1.0)
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    set_rp(1, "retracted", ctrl)
    set_rp(7, "retracted", ctrl)
    time.sleep(1.5)
    # Reset 0&6 to B
    set_g(0, 'B', ctrl)
    set_g(6, 'B', ctrl)
    time.sleep(1.0)
    # Transfer back
    ctrl.setSpeed(1, 30)
    ctrl.setSpeed(7, 30)
    set_rp(1, "hold", ctrl)
    set_rp(7, "hold", ctrl)
    time.sleep(1.0)
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    set_rp(3, "retracted", ctrl)
    set_rp(9, "retracted", ctrl)
    time.sleep(1.5)

def main():
    print("Connecting to Maestro...")
    ctrl = maestro.Controller('/dev/ttyACM0')
    for ch in [0, 2, 6, 8]:
        ctrl.setAccel(ch, GRIPPER_ACCEL)
    
    print("Opening camera...")
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("❌ Camera failed")
        ctrl.close()
        return
    
    try:
        # Engage cube
        print("\n═══ ENGAGING CUBE ═══")
        engage_all(ctrl)
        
        # Setup for Y rotations (grippers 2&8 control, clear camera view)
        print("\n═══ SETUP FOR Y ROTATIONS ═══")
        y_setup(ctrl)
        
        # Photo 1: Starting position (White front)
        print("\n═══ PHOTO 1: Starting position ═══")
        print("Expected: WHITE (W)")
        take_photo("01_start_W", cam)
        input("Press Enter to continue...")
        
        # Y 180°
        print("\n═══ Y 180° ═══")
        print("Moving 2: C→A, 8: A→C")
        set_g(2, 'A', ctrl)
        set_g(8, 'C', ctrl)
        time.sleep(2.0)
        print("Expected: YELLOW (Y)")
        take_photo("02_y180_Y", cam)
        input("Press Enter to continue...")
        
        # Y 90° CW (need to reset to B first)
        print("\n═══ Y 90° CW ═══")
        y_reset_to_b(ctrl)
        print("Moving 2: B→A, 8: B→C")
        set_g(2, 'A', ctrl)
        set_g(8, 'C', ctrl)
        time.sleep(2.0)
        print("Expected: ??? (let's find out)")
        take_photo("03_y90cw", cam)
        input("Press Enter to continue...")
        
        # Y 90° CCW from current (reset, then opposite direction)
        print("\n═══ Y 90° CCW ═══")
        y_reset_to_b(ctrl)
        print("Moving 2: B→C, 8: B→A")
        set_g(2, 'C', ctrl)
        set_g(8, 'A', ctrl)
        time.sleep(2.0)
        print("Expected: ??? (let's find out)")
        take_photo("04_y90ccw", cam)
        input("Press Enter to continue...")
        
        # X rotation test
        print("\n═══ SETUP FOR X ROTATION ═══")
        x_setup(ctrl)
        
        # X 90° forward
        print("\n═══ X 90° FORWARD ═══")
        print("Moving 0: B→C, 6: B→A (slow)")
        ctrl.setSpeed(0, X_SPEED[0])
        ctrl.setSpeed(6, X_SPEED[6])
        set_g(0, 'C', ctrl)
        set_g(6, 'A', ctrl)
        time.sleep(2.5)
        ctrl.setSpeed(0, 0)
        ctrl.setSpeed(6, 0)
        print("Expected: ??? (let's find out)")
        take_photo("05_x90fwd", cam)
        input("Press Enter to continue...")
        
        # X 90° backward (from current)
        print("\n═══ X 90° BACKWARD ═══")
        print("Moving 0: C→B, 6: A→B first...")
        x_reset_to_b(ctrl)
        x_setup(ctrl)
        print("Moving 0: B→A, 6: B→C (slow)")
        ctrl.setSpeed(0, X_SPEED[0])
        ctrl.setSpeed(6, X_SPEED[6])
        set_g(0, 'A', ctrl)
        set_g(6, 'C', ctrl)
        time.sleep(2.5)
        ctrl.setSpeed(0, 0)
        ctrl.setSpeed(6, 0)
        print("Expected: ??? (let's find out)")
        take_photo("06_x90back", cam)
        input("Press Enter to continue...")
        
        print("\n═══ DONE ═══")
        print("Check the photos in ~/rcubed/test_*.jpg")
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted")
    finally:
        cam.release()
        ctrl.close()

if __name__ == '__main__':
    main()
