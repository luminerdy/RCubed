#!/usr/bin/env python3
"""
RCubed Training Data Collection v2
Based on scan_v7.py (verified 2026-03-31)

Workflow:
1. Scan all 6 faces → save to training_scans/scan_XXX/
2. Scramble cube (3-6 random moves)
3. Repeat

Usage:
  python3 collect_training_v2.py           # Interactive, runs until stopped
  python3 collect_training_v2.py --count 10  # Collect 10 scans then stop
"""

import sys
import os
import time
import random
import shutil
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maestro

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
TRAINING_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "training_scans")

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
        self.F, self.D, self.B, self.U = self.U, self.F, self.D, self.B
    
    def x_back(self):
        self.F, self.U, self.B, self.D = self.D, self.F, self.U, self.B
    
    def name(self, c):
        return {'W':'White','Y':'Yellow','R':'Red','O':'Orange','B':'Blue','G':'Green'}[c]

# ─── Helpers ────────────────────────────────────────────────────────────────

grip = {0: 'B', 2: 'C', 6: 'B', 8: 'A'}

def set_g(ch, pos, ctrl):
    ctrl.setTarget(ch, GRIPPER[ch][pos] * 4)
    grip[ch] = pos

def set_rp(ch, pos, ctrl):
    ctrl.setTarget(ch, RP[ch][pos] * 4)

def wait(t=1.0):
    time.sleep(t)

def photo(name, num, scan_dir, cam, rotation=None):
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
    path = os.path.join(scan_dir, f"face_{num}_{name}.jpg")
    cv2.imwrite(path, img)
    return path

# ─── Rotation Primitives (from scan_v7.py) ──────────────────────────────────

def y_180(ctrl, cube):
    if grip[2] == 'C':
        set_g(2, 'A', ctrl)
        set_g(8, 'C', ctrl)
    else:
        set_g(2, 'C', ctrl)
        set_g(8, 'A', ctrl)
    wait(2.0)
    cube.y_180()

def y_90_cw(ctrl, cube):
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
    set_g(2, 'B', ctrl)
    set_g(8, 'B', ctrl)
    wait()
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
    set_g(2, 'A', ctrl)
    set_g(8, 'C', ctrl)
    wait(2.0)
    cube.y_cw()

def y_90_ccw(ctrl, cube):
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
    set_g(2, 'B', ctrl)
    set_g(8, 'B', ctrl)
    wait()
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
    set_g(2, 'C', ctrl)
    set_g(8, 'A', ctrl)
    wait(2.0)
    cube.y_ccw()

def x_setup(ctrl):
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
    set_g(2, 'B', ctrl)
    set_g(8, 'B', ctrl)
    wait()

def x_90_fwd(ctrl, cube):
    ctrl.setSpeed(0, X_SPEED[0])
    ctrl.setSpeed(6, X_SPEED[6])
    set_g(0, 'C', ctrl)
    set_g(6, 'A', ctrl)
    wait(2.5)
    ctrl.setSpeed(0, 0)
    ctrl.setSpeed(6, 0)
    cube.x_fwd()

def x_reset(ctrl):
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

def x_180_fwd(ctrl, cube):
    ctrl.setSpeed(0, X_SPEED[0])
    ctrl.setSpeed(6, X_SPEED[6])
    set_g(0, 'C', ctrl)
    set_g(6, 'A', ctrl)
    wait(2.5)
    ctrl.setSpeed(0, 0)
    ctrl.setSpeed(6, 0)
    cube.x_fwd()
    
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
    
    ctrl.setSpeed(0, X_SPEED[0])
    ctrl.setSpeed(6, X_SPEED[6])
    set_g(0, 'C', ctrl)
    set_g(6, 'A', ctrl)
    wait(2.5)
    ctrl.setSpeed(0, 0)
    ctrl.setSpeed(6, 0)
    cube.x_fwd()

# ─── Face Turn for Scrambling ───────────────────────────────────────────────

def face_turn(ctrl, gripper, direction):
    """Turn a single face. Assumes all RPs holding, all grippers at B."""
    rp = {0: 1, 2: 3, 6: 7, 8: 9}[gripper]
    target = {'cw': 'C', 'ccw': 'A', '180': 'D'}[direction]
    
    # Turn
    set_g(gripper, target, ctrl)
    delay = 2.0 if direction == '180' else 1.2
    wait(delay)
    
    # Reset gripper
    ctrl.setSpeed(rp, 0)
    set_rp(rp, "retracted", ctrl)
    wait(2.0)
    set_g(gripper, 'B', ctrl)
    wait(0.6)
    ctrl.setSpeed(rp, 30)
    set_rp(rp, "hold", ctrl)
    wait(1.5)

def reset_grippers_to_b(ctrl):
    """Reset all grippers to B position safely for scrambling."""
    # Transfer hold to 3&9
    ctrl.setSpeed(3, 30)
    ctrl.setSpeed(9, 30)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    wait(2.0)
    # Retract 1&7
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    set_rp(1, "retracted", ctrl)
    set_rp(7, "retracted", ctrl)
    wait(2.0)
    # Reset 0&6 to B
    set_g(0, 'B', ctrl)
    set_g(6, 'B', ctrl)
    wait(1.0)
    # Re-engage 1&7
    ctrl.setSpeed(1, 30)
    ctrl.setSpeed(7, 30)
    set_rp(1, "hold", ctrl)
    set_rp(7, "hold", ctrl)
    wait(2.0)
    # 2&8 should already be at B, but ensure
    # (Can't easily reset 2&8 without another transfer, skip for now)

def scramble(ctrl, num_moves=None):
    """Execute random face turns to scramble the cube."""
    # First ensure all grippers at B
    reset_grippers_to_b(ctrl)
    
    if num_moves is None:
        num_moves = random.randint(3, 6)
    
    moves = []
    grippers = [0, 2, 6, 8]  # L, U, R, D
    directions = ['cw', 'ccw', '180']
    names = {0: 'L', 2: 'U', 6: 'R', 8: 'D'}
    
    for _ in range(num_moves):
        g = random.choice(grippers)
        d = random.choice(directions)
        move_name = names[g] + ("'" if d == 'ccw' else "2" if d == '180' else "")
        moves.append(move_name)
        face_turn(ctrl, g, d)
    
    return moves

# ─── Scan Sequence ──────────────────────────────────────────────────────────

def scan_cube(ctrl, cam, scan_dir):
    """Scan all 6 faces. Returns cube tracker."""
    cube = Cube()
    faces = []
    
    for ch in [0, 2, 6, 8]:
        ctrl.setAccel(ch, 110)
    
    # Y setup
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
    faces.append(photo("front", 1, scan_dir, cam))
    
    # 2. Y 180° → Back
    y_180(ctrl, cube)
    faces.append(photo("back", 2, scan_dir, cam))
    
    # 3. Y 90° CW → Right
    y_90_cw(ctrl, cube)
    faces.append(photo("right", 3, scan_dir, cam))
    
    # 4. Y 180° → Left
    y_180(ctrl, cube)
    faces.append(photo("left", 4, scan_dir, cam))
    
    # 5. Y 90° CCW → Return to White front
    y_90_ccw(ctrl, cube)
    
    # 6. X 90° fwd → Top
    x_setup(ctrl)
    x_90_fwd(ctrl, cube)
    faces.append(photo("top", 5, scan_dir, cam, 'CW90'))
    
    # 7. X 180° fwd → Bottom
    x_reset(ctrl)
    x_setup(ctrl)
    x_180_fwd(ctrl, cube)
    faces.append(photo("bottom", 6, scan_dir, cam, 'CCW90'))
    
    # 8. Return to White front
    x_reset(ctrl)
    x_setup(ctrl)
    x_90_fwd(ctrl, cube)
    
    # 9. Final hold
    ctrl.setSpeed(3, 30)
    ctrl.setSpeed(9, 30)
    set_rp(3, "hold", ctrl)
    set_rp(9, "hold", ctrl)
    wait(1.5)
    
    return cube, faces

def get_next_scan_number():
    """Find the next available scan number."""
    os.makedirs(TRAINING_DIR, exist_ok=True)
    existing = [d for d in os.listdir(TRAINING_DIR) if d.startswith("scan_")]
    if not existing:
        return 1
    nums = [int(d.split("_")[1]) for d in existing if d.split("_")[1].isdigit()]
    return max(nums) + 1 if nums else 1

# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Collect training data')
    parser.add_argument('--count', type=int, default=0, help='Number of scans (0=unlimited)')
    parser.add_argument('--continue', dest='cont', action='store_true', help='Continue without setup (cube already loaded)')
    args = parser.parse_args()
    
    print("Connecting to Maestro...")
    ctrl = maestro.Controller('/dev/ttyACM0')
    
    print("Opening camera...")
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("❌ Camera failed")
        ctrl.close()
        return
    
    for ch in [0, 2, 6, 8]:
        ctrl.setAccel(ch, 110)
    
    if args.cont:
        print("\n═══ CONTINUING (cube already loaded) ═══")
        # First ensure all RPs are holding
        for ch in [1, 3, 7, 9]:
            ctrl.setSpeed(ch, 30)
            set_rp(ch, "hold", ctrl)
        wait(1.5)
        # Reset all grippers to safe positions (B for all)
        print("  Resetting grippers to safe positions...")
        reset_grippers_to_b(ctrl)
        # Also reset 2&8 to scan start position (C/A) safely
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
        set_g(2, 'C', ctrl)
        set_g(8, 'A', ctrl)
        wait(1.0)
        ctrl.setSpeed(3, 30)
        ctrl.setSpeed(9, 30)
        set_rp(3, "hold", ctrl)
        set_rp(9, "hold", ctrl)
        wait(1.5)
    else:
        # Initial setup
        print("\n═══ INITIAL SETUP ═══")
        set_g(0, 'B', ctrl)
        set_g(6, 'B', ctrl)
        set_g(2, 'C', ctrl)
        set_g(8, 'A', ctrl)
        for ch in [1, 3, 7, 9]:
            ctrl.setSpeed(ch, 0)
            set_rp(ch, "retracted", ctrl)
        wait()
        
        input("⏳ Load cube (White front, Blue top, Red right), press Enter...")
        
        # Engage
        for ch in [1, 3, 7, 9]:
            ctrl.setSpeed(ch, 30)
            set_rp(ch, "hold", ctrl)
        wait(1.5)
    
    scan_num = get_next_scan_number()
    scans_done = 0
    
    try:
        while True:
            scan_dir = os.path.join(TRAINING_DIR, f"scan_{scan_num:03d}")
            os.makedirs(scan_dir, exist_ok=True)
            
            print(f"\n═══ SCAN {scan_num} ═══")
            cube, faces = scan_cube(ctrl, cam, scan_dir)
            print(f"  ✅ Saved {len([f for f in faces if f])}/6 faces to {scan_dir}")
            
            scans_done += 1
            if args.count > 0 and scans_done >= args.count:
                print(f"\n✅ Collected {scans_done} scans. Done!")
                break
            
            # Scramble
            print(f"\n═══ SCRAMBLE ═══")
            moves = scramble(ctrl)
            print(f"  Moves: {' '.join(moves)}")
            
            scan_num += 1
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️ Stopped. Collected {scans_done} scans.")
    finally:
        # Release cube
        print("\n═══ RELEASE ═══")
        for ch in [1, 3, 7, 9]:
            ctrl.setSpeed(ch, 0)
            set_rp(ch, "retracted", ctrl)
        wait(1.5)
        cam.release()
        ctrl.close()
        print("Done.")

if __name__ == '__main__':
    main()
