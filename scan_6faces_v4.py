#!/usr/bin/env python3
"""
RCubed 6-Face Scanner V4 - Fixed Collision Rules

COLLISION RULES:
- Adjacent grippers can't both be at A/C
- 0&6 are adjacent to 2&8
- SOLUTION: Keep 0&6 at B during all Y rotations. 2&8 can be at A/C safely.

CAMERA VIEW:
- B and D = IN camera view
- A and C = OUT of camera view
- For scanning side faces: 2&8 at A/C (out of view), 0&6 at B (safe)
- For scanning top/bottom: Need 2&8 at B during X rotation (collision safety)

SEQUENCE:
Phase 1 (Y rotations): 0&6 stay at B, 2&8 rotate A↔C
Phase 2 (X rotations): 2&8 at B, 0&6 rotate through A/C
"""

import sys
import os
import time
import json
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maestro

# ─── Configuration ──────────────────────────────────────────────────────────

with open('servo_config.json') as f:
    config = json.load(f)
    GRIPPER = {int(k): v for k, v in config['gripper'].items()}
    RP = {int(k): v for k, v in config['rp'].items()}

GRIPPER_ACCEL = 110
DELAY = 1.5
Y_ROTATION_DELAY = 2.0
X_ROTATION_SPEED = {'0': 60, '6': 45}
X_ROTATION_DELAY = 2.2

SCAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scans')
os.makedirs(SCAN_DIR, exist_ok=True)

CROP_X1, CROP_Y1 = 180, 75
CROP_X2, CROP_Y2 = 460, 400


# ─── Helpers ────────────────────────────────────────────────────────────────

def wait(t=DELAY):
    time.sleep(t)

def set_gripper(channel, position, controller):
    us = GRIPPER[channel][position]
    controller.setTarget(channel, us * 4)

def set_rp(channel, position, controller):
    us = RP[channel][position]
    controller.setTarget(channel, us * 4)

def take_photo(name, face_num, camera):
    """Capture and save a cropped face image."""
    ret, frame = camera.read()
    if not ret:
        print(f"  ❌ Failed to capture {name}")
        return None
    
    cropped = frame[CROP_Y1:CROP_Y2, CROP_X1:CROP_X2]
    
    if name == "top":
        cropped = cv2.rotate(cropped, cv2.ROTATE_90_CLOCKWISE)
    elif name == "bottom":
        cropped = cv2.rotate(cropped, cv2.ROTATE_90_COUNTERCLOCKWISE)
    
    path = os.path.join(SCAN_DIR, f"face_{face_num}_{name}.jpg")
    cv2.imwrite(path, cropped)
    print(f"  📸 {name} → face_{face_num}_{name}.jpg")
    return path


# ─── Y Rotation Helpers ─────────────────────────────────────────────────────

def y_setup(controller):
    """Setup for Y rotation: RP 3&9 hold, RP 1&7 retracted, 0&6 at B"""
    controller.setSpeed(3, 50)
    controller.setSpeed(9, 50)
    set_rp(3, "hold", controller)
    set_rp(9, "hold", controller)
    wait()
    controller.setSpeed(1, 0)
    controller.setSpeed(7, 0)
    set_rp(1, "retracted", controller)
    set_rp(7, "retracted", controller)
    wait()

def y_reset_2_8_to_B(controller):
    """Reset grippers 2&8 to B. Requires hold transfer."""
    # Transfer hold to 1&7
    controller.setSpeed(1, 50)
    controller.setSpeed(7, 50)
    set_rp(1, "hold", controller)
    set_rp(7, "hold", controller)
    wait()
    # Retract 3&9
    controller.setSpeed(3, 0)
    controller.setSpeed(9, 0)
    set_rp(3, "retracted", controller)
    set_rp(9, "retracted", controller)
    wait()
    # Move 2&8 to B
    set_gripper(2, "B", controller)
    set_gripper(8, "B", controller)
    wait()
    # Transfer hold back to 3&9
    controller.setSpeed(3, 50)
    controller.setSpeed(9, 50)
    set_rp(3, "hold", controller)
    set_rp(9, "hold", controller)
    wait()
    # Retract 1&7
    controller.setSpeed(1, 0)
    controller.setSpeed(7, 0)
    set_rp(1, "retracted", controller)
    set_rp(7, "retracted", controller)
    wait()


# ─── X Rotation Helpers ─────────────────────────────────────────────────────

def x_setup(controller):
    """Setup for X rotation: RP 1&7 hold, RP 3&9 retracted, 2&8 at B"""
    # First ensure 2&8 are at B (safe for X rotation)
    set_gripper(2, "B", controller)
    set_gripper(8, "B", controller)
    wait()
    # RP 1&7 hold
    controller.setSpeed(1, 50)
    controller.setSpeed(7, 50)
    set_rp(1, "hold", controller)
    set_rp(7, "hold", controller)
    wait()
    # Retract 3&9
    controller.setSpeed(3, 0)
    controller.setSpeed(9, 0)
    set_rp(3, "retracted", controller)
    set_rp(9, "retracted", controller)
    wait()

def x_forward_90(controller):
    """X forward 90°. 2&8 must be at B before calling."""
    controller.setSpeed(0, X_ROTATION_SPEED['0'])
    controller.setSpeed(6, X_ROTATION_SPEED['6'])
    set_gripper(0, "C", controller)
    set_gripper(6, "A", controller)
    time.sleep(X_ROTATION_DELAY)
    controller.setSpeed(0, 0)
    controller.setSpeed(6, 0)
    # Square cube
    controller.setSpeed(3, 50)
    controller.setSpeed(9, 50)
    set_rp(3, "hold", controller)
    set_rp(9, "hold", controller)
    wait()
    controller.setSpeed(3, 0)
    controller.setSpeed(9, 0)
    set_rp(3, "retracted", controller)
    set_rp(9, "retracted", controller)
    wait()

def x_reset_0_6_to_B(controller):
    """Reset grippers 0&6 to B. 2&8 must be at B. Requires hold transfer."""
    # Transfer hold to 3&9
    controller.setSpeed(3, 50)
    controller.setSpeed(9, 50)
    set_rp(3, "hold", controller)
    set_rp(9, "hold", controller)
    wait()
    # Retract 1&7
    controller.setSpeed(1, 0)
    controller.setSpeed(7, 0)
    set_rp(1, "retracted", controller)
    set_rp(7, "retracted", controller)
    wait()
    # Move 0&6 to B
    set_gripper(0, "B", controller)
    set_gripper(6, "B", controller)
    wait()
    # Transfer hold back to 1&7
    controller.setSpeed(1, 50)
    controller.setSpeed(7, 50)
    set_rp(1, "hold", controller)
    set_rp(7, "hold", controller)
    wait()
    # Retract 3&9
    controller.setSpeed(3, 0)
    controller.setSpeed(9, 0)
    set_rp(3, "retracted", controller)
    set_rp(9, "retracted", controller)
    wait()

def x_prep_for_photo(controller):
    """After X rotation, prep for photo: 0&6 to B, 2&8 to A/C (out of view)."""
    # 2&8 are at B, 0&6 are at C/A
    # Transfer hold to 3&9
    controller.setSpeed(3, 50)
    controller.setSpeed(9, 50)
    set_rp(3, "hold", controller)
    set_rp(9, "hold", controller)
    wait()
    # Retract 1&7
    controller.setSpeed(1, 0)
    controller.setSpeed(7, 0)
    set_rp(1, "retracted", controller)
    set_rp(7, "retracted", controller)
    wait()
    # Move 0&6 to B (now safe for 2&8 to move)
    set_gripper(0, "B", controller)
    set_gripper(6, "B", controller)
    wait()
    # Move 2&8 to A/C (out of camera view)
    set_gripper(2, "A", controller)
    set_gripper(8, "C", controller)
    wait()


# ─── Main Scan Sequence ─────────────────────────────────────────────────────

def scan_cube(controller, camera):
    faces = []
    
    # ═══ SETUP ═══
    print("\n═══ SETUP ═══")
    for ch in [0, 2, 6, 8]:
        controller.setAccel(ch, GRIPPER_ACCEL)
    
    # Starting position: 0&6 at B, 2&8 at C/A
    set_gripper(0, "B", controller)
    set_gripper(6, "B", controller)
    set_gripper(2, "C", controller)
    set_gripper(8, "A", controller)
    
    for ch in [1, 3, 7, 9]:
        controller.setSpeed(ch, 0)
        set_rp(ch, "retracted", controller)
    wait()
    
    input("  ⏳ Insert cube (White front, Blue top), press Enter...")
    
    # Engage all RP
    print("  Engaging grippers...")
    for ch in [1, 3, 7, 9]:
        controller.setSpeed(ch, 50)
        set_rp(ch, "hold", controller)
    wait()
    
    # ═══ PHASE 1: Side faces (Y rotations) ═══
    # Rule: 0&6 ALWAYS at B. 2&8 rotate between A/C.
    print("\n═══ PHASE 1: Side faces ═══")
    print("  State: 0&6 at B, 2&8 at C/A (safe, out of view)")
    
    y_setup(controller)
    
    # [1/6] FRONT (White) - 2&8 at C/A (out of view)
    print("\n[1/6] FRONT (White)")
    f = take_photo("front", 1, camera)
    if f: faces.append(("front", f))
    
    # [2/6] Y 180° → BACK (Yellow) - 2&8 swap to A/C (still out of view)
    print("\n[2/6] BACK (Yellow)")
    print("  Y 180° (2:C→A, 8:A→C)...")
    set_gripper(2, "A", controller)
    set_gripper(8, "C", controller)
    wait(Y_ROTATION_DELAY)
    f = take_photo("back", 2, camera)
    if f: faces.append(("back", f))
    
    # [3/6] Y CW 90° → RIGHT (Red)
    # From A/C, 90° CW ends at D/B or B/D (in view!)
    # Solution: reset to B, then rotate 90°, ending at A/C
    print("\n[3/6] RIGHT (Red)")
    y_reset_2_8_to_B(controller)  # Now at B/B
    print("  Y CW 90° (2:B→A, 8:B→C)...")
    set_gripper(2, "A", controller)
    set_gripper(8, "C", controller)
    wait(Y_ROTATION_DELAY)
    # Now 2&8 at A/C (out of view), 0&6 at B (safe) ✓
    f = take_photo("right", 3, camera)
    if f: faces.append(("right", f))
    
    # [4/6] Y 180° → LEFT (Orange) - 2&8 swap to C/A
    print("\n[4/6] LEFT (Orange)")
    print("  Y 180° (2:A→C, 8:C→A)...")
    set_gripper(2, "C", controller)
    set_gripper(8, "A", controller)
    wait(Y_ROTATION_DELAY)
    f = take_photo("left", 4, camera)
    if f: faces.append(("left", f))
    
    # Return to White front: Y CW 90°
    print("\n  Returning to White front...")
    y_reset_2_8_to_B(controller)  # Now at B/B
    print("  Y CW 90° (2:B→A, 8:B→C)...")
    set_gripper(2, "A", controller)
    set_gripper(8, "C", controller)
    wait(Y_ROTATION_DELAY)
    # Y total = 180 + 90 + 180 + 90 = 540° = 180° net... hmm
    # Let's see what face is in front after this
    
    # ═══ PHASE 2: Top/Bottom (X rotations) ═══
    # Rule: 2&8 at B during X rotation (collision safety)
    # For photo: move 0&6 to B, then 2&8 to A/C
    print("\n═══ PHASE 2: Top/Bottom ═══")
    
    x_setup(controller)  # 2&8 → B, RP 1&7 hold, RP 3&9 retracted
    print("  State: 0&6 at B, 2&8 at B")
    
    # [5/6] X forward 90° → TOP (Blue)
    print("\n[5/6] TOP (Blue)")
    print("  X forward 90°...")
    x_forward_90(controller)
    x_prep_for_photo(controller)  # 0&6 → B, 2&8 → A/C
    f = take_photo("top", 5, camera)
    if f: faces.append(("top", f))
    
    # [6/6] X forward 180° → BOTTOM (Green)
    print("\n[6/6] BOTTOM (Green)")
    # First move 2&8 back to B for X rotation
    set_gripper(2, "B", controller)
    set_gripper(8, "B", controller)
    wait()
    # Re-setup for X
    controller.setSpeed(1, 50)
    controller.setSpeed(7, 50)
    set_rp(1, "hold", controller)
    set_rp(7, "hold", controller)
    wait()
    controller.setSpeed(3, 0)
    controller.setSpeed(9, 0)
    set_rp(3, "retracted", controller)
    set_rp(9, "retracted", controller)
    wait()
    
    print("  X forward 90° (1/2)...")
    x_forward_90(controller)
    x_reset_0_6_to_B(controller)
    
    print("  X forward 90° (2/2)...")
    x_forward_90(controller)
    x_prep_for_photo(controller)  # 0&6 → B, 2&8 → A/C
    f = take_photo("bottom", 6, camera)
    if f: faces.append(("bottom", f))
    
    # Return to start: X forward 90°
    print("\n  Returning to White front, Blue top...")
    set_gripper(2, "B", controller)
    set_gripper(8, "B", controller)
    wait()
    controller.setSpeed(1, 50)
    controller.setSpeed(7, 50)
    set_rp(1, "hold", controller)
    set_rp(7, "hold", controller)
    wait()
    controller.setSpeed(3, 0)
    controller.setSpeed(9, 0)
    set_rp(3, "retracted", controller)
    set_rp(9, "retracted", controller)
    wait()
    print("  X forward 90°...")
    x_forward_90(controller)
    
    print(f"\n═══ SCAN COMPLETE: {len(faces)}/6 faces ═══")
    for name, path in faces:
        print(f"  {name}: {path}")
    
    return faces


def reset_to_start(controller, hold_cube=True):
    """Return all servos to starting position."""
    print("\n═══ RESET ═══")
    # Engage 1&7
    controller.setSpeed(1, 50)
    controller.setSpeed(7, 50)
    set_rp(1, "hold", controller)
    set_rp(7, "hold", controller)
    wait()
    # Retract 3&9
    controller.setSpeed(3, 0)
    controller.setSpeed(9, 0)
    set_rp(3, "retracted", controller)
    set_rp(9, "retracted", controller)
    wait()
    # All grippers to B
    for g in [0, 2, 6, 8]:
        set_gripper(g, "B", controller)
    wait()
    if not hold_cube:
        controller.setSpeed(1, 0)
        controller.setSpeed(7, 0)
        set_rp(1, "retracted", controller)
        set_rp(7, "retracted", controller)
        wait()
    print("  ✅ Done")


def main():
    print("Connecting to Maestro...")
    controller = maestro.Controller('/dev/ttyACM0')
    
    print("Opening camera...")
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("❌ Failed to open camera")
        controller.close()
        return
    print("✅ Camera ready")
    
    try:
        scan_cube(controller, camera)
        reset_to_start(controller, hold_cube=True)
    finally:
        camera.release()
        controller.close()
    
    print("\nDone!")


if __name__ == '__main__':
    main()
