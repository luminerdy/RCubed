#!/usr/bin/env python3
"""Single test: X 90° backward from White front, Blue top."""

import sys
import os
import time
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maestro

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

CROP = (180, 75, 460, 400)
X_SPEED = {0: 60, 6: 45}

def set_g(ch, pos, ctrl):
    ctrl.setTarget(ch, GRIPPER[ch][pos] * 4)

def set_rp(ch, pos, ctrl):
    ctrl.setTarget(ch, RP[ch][pos] * 4)

def take_photo(name, cam):
    time.sleep(0.3)
    for _ in range(3):
        cam.read()
    ret, frame = cam.read()
    if ret:
        x1, y1, x2, y2 = CROP
        cropped = frame[y1:y2, x1:x2]
        path = f"/home/luminerdy/rcubed/{name}.jpg"
        cv2.imwrite(path, cropped)
        print(f"📸 Saved: {path}")
        return path
    return None

def main():
    print("Connecting...")
    ctrl = maestro.Controller('/dev/ttyACM0')
    for ch in [0, 2, 6, 8]:
        ctrl.setAccel(ch, 110)
    
    print("Opening camera...")
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("❌ Camera failed")
        ctrl.close()
        return
    
    try:
        # Engage all
        print("\n═══ ENGAGING ═══")
        for ch in [1, 3, 7, 9]:
            ctrl.setSpeed(ch, 30)
            set_rp(ch, "hold", ctrl)
        time.sleep(1.5)
        
        # Photo before
        print("\n═══ BEFORE: Should be WHITE ═══")
        take_photo("test_x_before", cam)
        
        # Setup for X: RP 1&7 hold, RP 3&9 retracted, 2&8 at B
        print("\n═══ SETUP FOR X ═══")
        ctrl.setSpeed(3, 0)
        ctrl.setSpeed(9, 0)
        set_rp(3, "retracted", ctrl)
        set_rp(9, "retracted", ctrl)
        time.sleep(1.5)
        set_g(2, 'B', ctrl)
        set_g(8, 'B', ctrl)
        time.sleep(1.0)
        
        # X 90° backward: 0:B→A, 6:B→C
        print("\n═══ X 90° BACKWARD ═══")
        print("Moving 0: B→A, 6: B→C")
        print("Expected result: GREEN (D) comes to front")
        ctrl.setSpeed(0, X_SPEED[0])
        ctrl.setSpeed(6, X_SPEED[6])
        set_g(0, 'A', ctrl)
        set_g(6, 'C', ctrl)
        time.sleep(2.5)
        ctrl.setSpeed(0, 0)
        ctrl.setSpeed(6, 0)
        
        # Photo after
        print("\n═══ AFTER ═══")
        take_photo("test_x_after", cam)
        
        print("\nCheck test_x_after.jpg - should be GREEN")
        
    finally:
        cam.release()
        ctrl.close()

if __name__ == '__main__':
    main()
