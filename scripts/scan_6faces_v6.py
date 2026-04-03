#!/usr/bin/env python3
"""
RCubed 6-Face Scanner V6 - Minimal Moves with Correct Image Rotations

Kociemba expects: UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB
Cube orientation: White=F, Yellow=B, Red=R, Orange=L, Blue=U, Green=D

Image rotation rules:
- Side faces (F,B,R,L): "up" in image = Blue (U) edge
- Top face (U): "up" in image = Yellow (B) edge  
- Bottom face (D): "up" in image = White (F) edge

Scan sequence (5 rotations):
1. Scan Front (White) - no rotation needed, Blue is up
2. Y 180° → Scan Back (Yellow) - no rotation needed, Blue is up
3. Y 90° CW → Scan Right (Red) - no rotation needed, Blue is up
4. Y 180° → Scan Left (Orange) - no rotation needed, Blue is up
5. X 90° → Scan Top (Blue) - need rotation based on which edge is up
6. X 180° → Scan Bottom (Green) - need rotation based on which edge is up
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

class Cube:
    def __init__(self):
        # Standard: White=F, Yellow=B, Red=R, Orange=L, Blue=U, Green=D
        self.F, self.B = 'W', 'Y'
        self.R, self.L = 'R', 'O'  
        self.U, self.D = 'B', 'G'
    
    def y_cw(self):
        """Y CW 90°: L→F→R→B→L"""
        self.F, self.R, self.B, self.L = self.L, self.F, self.R, self.B
    
    def y_180(self):
        """Y 180°"""
        self.F, self.B = self.B, self.F
        self.R, self.L = self.L, self.R
    
    def x_fwd(self):
        """X forward 90°: U→F→D→B→U"""
        self.F, self.D, self.B, self.U = self.U, self.F, self.B, self.D
    
    def name(self, c):
        return {'W':'White','Y':'Yellow','R':'Red','O':'Orange','B':'Blue','G':'Green'}[c]
    
    def __str__(self):
        return f"F={self.F} B={self.B} R={self.R} L={self.L} U={self.U} D={self.D}"

cube = Cube()
gripper = {0:'B', 2:'C', 6:'B', 8:'A'}

def wait(t=DELAY):
    time.sleep(t)

def set_g(ch, pos, ctrl):
    ctrl.setTarget(ch, GRIPPER[ch][pos] * 4)
    gripper[ch] = pos

def set_rp(ch, pos, ctrl):
    ctrl.setTarget(ch, RP[ch][pos] * 4)

def photo(face_name, num, cam, rotation=None):
    """
    Take photo and apply rotation if needed.
    rotation: None, 'CW90', 'CCW90', '180'
    """
    ret, frame = cam.read()
    if not ret:
        return None
    cropped = frame[CROP_Y1:CROP_Y2, CROP_X1:CROP_X2]
    
    if rotation == 'CW90':
        cropped = cv2.rotate(cropped, cv2.ROTATE_90_CLOCKWISE)
    elif rotation == 'CCW90':
        cropped = cv2.rotate(cropped, cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif rotation == '180':
        cropped = cv2.rotate(cropped, cv2.ROTATE_180)
    
    path = os.path.join(SCAN_DIR, f"face_{num}_{face_name}.jpg")
    cv2.imwrite(path, cropped)
    rot_str = f" [rot {rotation}]" if rotation else ""
    print(f"  📸 {face_name} ({cube.name(cube.F)}){rot_str}")
    return path

# ─── Rotation Functions ─────────────────────────────────────────────────────

def y_180(ctrl):
    """Y 180° - just swap gripper positions"""
    print(f"  Y 180°")
    if gripper[2] == 'C':
        set_g(2, 'A', ctrl)
        set_g(8, 'C', ctrl)
    else:
        set_g(2, 'C', ctrl)
        set_g(8, 'A', ctrl)
    wait(Y_DELAY)
    cube.y_180()
    print(f"    → {cube}")

def y_90(ctrl):
    """Y 90° CW - need to reset grippers to B first"""
    print(f"  Y 90° CW")
    # Transfer hold to 0&6
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
    # Reset 2&8 to B
    set_g(2, 'B', ctrl)
    set_g(8, 'B', ctrl)
    wait()
    # Transfer back to 2&8
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
    # Rotate: 2:B→A, 8:B→C
    set_g(2, 'A', ctrl)
    set_g(8, 'C', ctrl)
    wait(Y_DELAY)
    cube.y_cw()
    print(f"    → {cube}")

def y_ccw_90(ctrl):
    """Y 90° CCW - need to reset grippers to B first"""
    print(f"  Y 90° CCW")
    # Transfer hold to 0&6
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
    # Reset 2&8 to B
    set_g(2, 'B', ctrl)
    set_g(8, 'B', ctrl)
    wait()
    # Transfer back to 2&8
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
    # Rotate CCW: 2:B→C, 8:B→A
    set_g(2, 'C', ctrl)
    set_g(8, 'A', ctrl)
    wait(Y_DELAY)
    # CCW is 3x CW
    cube.y_cw()
    cube.y_cw()
    cube.y_cw()
    print(f"    → {cube}")

def x_90(ctrl):
    """X forward 90°"""
    print(f"  X fwd 90°")
    ctrl.setSpeed(0, X_SPEED['0'])
    ctrl.setSpeed(6, X_SPEED['6'])
    set_g(0, 'C', ctrl)
    set_g(6, 'A', ctrl)
    time.sleep(X_DELAY)
    ctrl.setSpeed(0, 0)
    ctrl.setSpeed(6, 0)
    # Square
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
    cube.x_fwd()
    print(f"    → {cube}")

def x_back_90(ctrl):
    """X backward 90°"""
    print(f"  X back 90°")
    ctrl.setSpeed(0, X_SPEED['0'])
    ctrl.setSpeed(6, X_SPEED['6'])
    set_g(0, 'A', ctrl)
    set_g(6, 'C', ctrl)
    time.sleep(X_DELAY)
    ctrl.setSpeed(0, 0)
    ctrl.setSpeed(6, 0)
    # Square
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
    # Back is 3x forward
    cube.x_fwd()
    cube.x_fwd()
    cube.x_fwd()
    print(f"    → {cube}")

def reset_0_6(ctrl):
    """Reset 0&6 to B (2&8 must be at B)"""
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
    set_g(0, 'B', ctrl)
    set_g(6, 'B', ctrl)
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

def setup_for_y(ctrl):
    """RP 3&9 hold, 1&7 retracted"""
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

def setup_for_x(ctrl):
    """RP 1&7 hold, 3&9 retracted, 2&8 at B"""
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
    set_g(2, 'B', ctrl)
    set_g(8, 'B', ctrl)
    wait()

def prep_photo_x(ctrl):
    """After X rotation, move 2&8 to A/C for photo (0&6 must go to B first)"""
    reset_0_6(ctrl)
    set_g(2, 'A', ctrl)
    set_g(8, 'C', ctrl)
    wait()

# ─── Main ───────────────────────────────────────────────────────────────────

def scan(ctrl, cam):
    global cube
    cube = Cube()
    faces = []
    
    print("\n═══ SETUP ═══")
    print(f"  Start: {cube}")
    
    for ch in [0, 2, 6, 8]:
        ctrl.setAccel(ch, GRIPPER_ACCEL)
    
    set_g(0, 'B', ctrl)
    set_g(6, 'B', ctrl)
    set_g(2, 'C', ctrl)
    set_g(8, 'A', ctrl)
    
    for ch in [1, 3, 7, 9]:
        ctrl.setSpeed(ch, 0)
        set_rp(ch, "retracted", ctrl)
    wait()
    
    input("  ⏳ Insert cube (White front, Blue top), Enter...")
    
    for ch in [1, 3, 7, 9]:
        ctrl.setSpeed(ch, 50)
        set_rp(ch, "hold", ctrl)
    wait()
    
    # ═══ SCAN SIDE FACES ═══
    print("\n═══ SIDE FACES ═══")
    setup_for_y(ctrl)
    
    # 1. Front (White) - Blue is up, no rotation needed
    print("\n[1/6] FRONT (White)")
    print(f"  State: {cube}")
    faces.append(photo("front", 1, cam, None))
    
    # 2. Y 180° → Back (Yellow) - Blue still up, no rotation
    print("\n[2/6] BACK (Yellow)")
    y_180(ctrl)
    faces.append(photo("back", 2, cam, None))
    
    # 3. Y 90° CW → Right
    # After Y180+Y90: F=O→R (Left becomes Front... wait let me trace)
    # Start: F=W,B=Y,R=R,L=O,U=B,D=G
    # Y180: F=Y,B=W,R=O,L=R,U=B,D=G
    # Y90CW (L→F): F=R,B=O,R=Y,L=W,U=B,D=G
    # So Red is front, Blue still up - no rotation needed
    print("\n[3/6] RIGHT (Red)")
    y_90(ctrl)
    faces.append(photo("right", 3, cam, None))
    
    # 4. Y 180° → Left (Orange)
    # Y180: F=O,B=R,R=W,L=Y,U=B,D=G
    # Orange front, Blue still up - no rotation
    print("\n[4/6] LEFT (Orange)")
    y_180(ctrl)
    faces.append(photo("left", 4, cam, None))
    
    # ═══ SCAN TOP/BOTTOM ═══
    print("\n═══ TOP/BOTTOM ═══")
    
    # 5. X 90° → Top (Blue)
    # Before X: F=O,B=R,R=W,L=Y,U=B,D=G
    # X fwd: F=B,B=G,R=W,L=Y,U=R,D=O
    # Blue is now front. What edge is up? U=R (Red)
    # For Top face image: "up" should be Yellow (B) edge
    # Red is at top, Yellow is at... L (left)
    # So need to rotate image 90° CW to put Yellow edge at top
    print("\n[5/6] TOP (Blue)")
    setup_for_x(ctrl)
    x_90(ctrl)
    prep_photo_x(ctrl)
    faces.append(photo("top", 5, cam, 'CW90'))
    
    # 6. X 180° → Bottom (Green)
    # From Blue front: F=B,B=G,R=W,L=Y,U=R,D=O
    # X fwd: F=R,B=O,R=W,L=Y,U=G,D=B
    # X fwd: F=G,B=B,R=W,L=Y,U=O,D=R
    # Green is now front. What edge is up? U=O (Orange)
    # For Bottom face image: "up" should be White (F) edge
    # Orange is at top, White is at R (right)
    # So need to rotate image 90° CCW to put White edge at top
    print("\n[6/6] BOTTOM (Green)")
    setup_for_x(ctrl)
    x_90(ctrl)
    reset_0_6(ctrl)
    setup_for_x(ctrl)
    x_90(ctrl)
    prep_photo_x(ctrl)
    faces.append(photo("bottom", 6, cam, 'CCW90'))
    
    print(f"\n═══ SCANNED {len([f for f in faces if f])}/6 ═══")
    print(f"  Final: {cube}")
    
    # ═══ RETURN TO WHITE FRONT, BLUE TOP ═══
    print("\n═══ RETURN TO WHITE/BLUE ═══")
    # Current: F=G,B=B,R=W,L=Y,U=O,D=R
    # White is at R → Y CCW 90° brings R→F
    # Then: F=W,B=Y,R=G,L=B,U=O,D=R
    # Blue is at L → hmm, need different approach
    
    # Let me recalculate:
    # Y CCW: R→F, F→L, L→B, B→R
    # From F=G,R=W,L=Y,B=B: F=W,R=G,L=B,B=Y ✓ (White front, Yellow back)
    # U and D unchanged: U=O,D=R
    # Now need Blue on top. Blue is at L.
    # Can't get L to U with X rotation... need different sequence
    
    # Better: from F=G,B=B,R=W,L=Y,U=O,D=R
    # X back 90° (B→U): F=B,B=R,R=W,L=Y,U=G,D=O
    # Now Blue front. Y CCW 90°: F=W,B=Y,R=B,L=G,U=?,D=?
    # Wait, Y doesn't affect U/D. So U=G,D=O still. Not right.
    
    # Simpler: 
    # From F=G,B=B,R=W,L=Y,U=O,D=R
    # X fwd 90° (total 360° = back to Y-only rotations): F=O,B=R,R=W,L=Y,U=G,D=B
    # Hmm, this is getting complicated. Let me just do the moves:
    
    setup_for_x(ctrl)
    print("  Returning...")
    x_90(ctrl)  # One more X fwd to complete 360° on X axis
    # Now: F=O,B=R,R=W,L=Y,U=G,D=B
    
    # White at R, need Y CCW to bring to front
    setup_for_y(ctrl)
    y_ccw_90(ctrl)
    # Now: F=W,B=Y,R=O,L=R,U=G,D=B - but U=G, D=B (inverted!)
    
    # Need X back 90° to fix U/D
    setup_for_x(ctrl)
    x_back_90(ctrl)
    
    print(f"  Final: {cube}")
    
    return faces

def main():
    ctrl = maestro.Controller('/dev/ttyACM0')
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        ctrl.close()
        return
    
    try:
        scan(ctrl, cam)
        # Reset
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
            set_g(g, 'B', ctrl)
        print("  Done")
    finally:
        cam.release()
        ctrl.close()

if __name__ == '__main__':
    main()
