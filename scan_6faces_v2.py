#!/usr/bin/env python3
"""
RCubed 6-Face Scanner V2
Scans all 6 faces and returns to White front / Blue top.

Scan order: F, B, L, R, D, U
Return sequence: X backward 90° + Y 180°
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
SIMULTANEOUS_DELAY = 2.0
X_ROTATION_SPEED = {'0': 60, '6': 45}
X_ROTATION_DELAY = 2.2

SCAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scans')
os.makedirs(SCAN_DIR, exist_ok=True)

# Crop settings (face region in 640x480 image)
CROP_X1, CROP_Y1 = 180, 75
CROP_X2, CROP_Y2 = 460, 400


# ─── Helpers ────────────────────────────────────────────────────────────────

def wait(t=DELAY):
    time.sleep(t)

def set_gripper(channel, position, controller):
    us = GRIPPER[channel][position]
    controller.setTarget(channel, us * 4)
    print(f"  Gripper {channel} → {position} ({us} μs)")

def set_rp(channel, position, controller):
    us = RP[channel][position]
    controller.setTarget(channel, us * 4)
    print(f"  RP {channel} → {position} ({us} μs)")

def x_rotation_slow(pos0, pos6, controller):
    """Slow X rotation for grippers 0 and 6."""
    controller.setSpeed(0, X_ROTATION_SPEED['0'])
    controller.setSpeed(6, X_ROTATION_SPEED['6'])
    controller.setTarget(0, GRIPPER[0][pos0] * 4)
    controller.setTarget(6, GRIPPER[6][pos6] * 4)
    print(f"  Gripper 0 → {pos0} ({GRIPPER[0][pos0]} μs)")
    print(f"  Gripper 6 → {pos6} ({GRIPPER[6][pos6]} μs)")
    time.sleep(X_ROTATION_DELAY)
    controller.setSpeed(0, 0)
    controller.setSpeed(6, 0)

def take_photo(name, face_num, camera):
    """Capture and save a cropped face image."""
    ret, frame = camera.read()
    if not ret:
        print(f"  ❌ Failed to capture {name}")
        return None
    
    # Crop to face region
    cropped = frame[CROP_Y1:CROP_Y2, CROP_X1:CROP_X2]
    
    # Rotation corrections for U and D faces
    if name == "top":
        cropped = cv2.rotate(cropped, cv2.ROTATE_90_CLOCKWISE)
    elif name == "bottom":
        cropped = cv2.rotate(cropped, cv2.ROTATE_90_COUNTERCLOCKWISE)
    
    path = os.path.join(SCAN_DIR, f"face_{face_num}_{name}.jpg")
    cv2.imwrite(path, cropped)
    print(f"  📸 Face {face_num}: {name} → {path} [CROPPED]")
    return path


# ─── Y Rotation (around vertical axis) ──────────────────────────────────────

def y_rotate_180(controller):
    """Y 180° rotation using grippers 2 & 8."""
    # Assumes RP 3&9 holding, RP 1&7 retracted, grippers 2&8 ready
    print("  Y 180° rotation (2: swap, 8: swap)...")
    # Get current positions and swap
    # From C/A → A/C or from A/C → C/A
    controller.setTarget(2, GRIPPER[2]['A'] * 4)
    controller.setTarget(8, GRIPPER[8]['C'] * 4)
    wait(SIMULTANEOUS_DELAY)

def y_rotate_cw_90(controller):
    """Y CW 90° rotation. Requires reset to B first."""
    print("  Y CW 90° rotation (2: B→A, 8: B→C)...")
    controller.setTarget(2, GRIPPER[2]['A'] * 4)
    controller.setTarget(8, GRIPPER[8]['C'] * 4)
    wait(SIMULTANEOUS_DELAY)

def y_rotate_ccw_90(controller):
    """Y CCW 90° rotation. Requires reset to B first."""
    print("  Y CCW 90° rotation (2: B→C, 8: B→A)...")
    controller.setTarget(2, GRIPPER[2]['C'] * 4)
    controller.setTarget(8, GRIPPER[8]['A'] * 4)
    wait(SIMULTANEOUS_DELAY)

def reset_grippers_2_8_to_B(controller):
    """Reset grippers 2 & 8 to B position (requires hold transfer)."""
    print("  Engaging RP 1 & 7...")
    controller.setSpeed(1, 50)
    controller.setSpeed(7, 50)
    set_rp(1, "hold", controller)
    set_rp(7, "hold", controller)
    wait()
    
    print("  Retracting RP 3 & 9...")
    controller.setSpeed(3, 0)
    controller.setSpeed(9, 0)
    set_rp(3, "retracted", controller)
    set_rp(9, "retracted", controller)
    wait()
    
    print("  Resetting grippers 2 & 8 to B...")
    set_gripper(2, "B", controller)
    set_gripper(8, "B", controller)
    wait()
    
    print("  Engaging RP 3 & 9...")
    controller.setSpeed(3, 50)
    controller.setSpeed(9, 50)
    set_rp(3, "hold", controller)
    set_rp(9, "hold", controller)
    wait()
    
    print("  Retracting RP 1 & 7...")
    controller.setSpeed(1, 0)
    controller.setSpeed(7, 0)
    set_rp(1, "retracted", controller)
    set_rp(7, "retracted", controller)
    wait()


# ─── X Rotation (tumble forward/backward) ───────────────────────────────────

def x_rotate_forward_90(controller):
    """X forward 90° tumble using grippers 0 & 6."""
    # Assumes RP 1&7 holding, RP 3&9 retracted, grippers 0&6 at B
    print("  X forward 90° tumble (0: B→C, 6: B→A) [SLOW]...")
    x_rotation_slow("C", "A", controller)

def x_rotate_backward_90(controller):
    """X backward 90° tumble using grippers 0 & 6."""
    print("  X backward 90° tumble (0: B→A, 6: B→C) [SLOW]...")
    x_rotation_slow("A", "C", controller)

def x_rotate_180(controller):
    """X 180° tumble using grippers 0 & 6."""
    # From current position (C/A after forward) → opposite (A/C)
    print("  X 180° tumble (0: C→A, 6: A→C) [SLOW]...")
    x_rotation_slow("A", "C", controller)

def prep_for_x_rotation(controller):
    """Transfer hold to 0&6 for X rotation."""
    print("  Engaging RP 1 & 7...")
    controller.setSpeed(1, 50)
    controller.setSpeed(7, 50)
    set_rp(1, "hold", controller)
    set_rp(7, "hold", controller)
    wait()
    
    print("  Retracting RP 3 & 9...")
    controller.setSpeed(3, 0)
    controller.setSpeed(9, 0)
    set_rp(3, "retracted", controller)
    set_rp(9, "retracted", controller)
    wait()
    
    print("  Moving grippers 2 & 8 to B...")
    set_gripper(2, "B", controller)
    set_gripper(8, "B", controller)
    wait()

def reset_grippers_0_6_to_B(controller):
    """Reset grippers 0 & 6 to B position (requires hold transfer)."""
    print("  Engaging RP 3 & 9...")
    controller.setSpeed(3, 50)
    controller.setSpeed(9, 50)
    set_rp(3, "hold", controller)
    set_rp(9, "hold", controller)
    wait()
    
    print("  Retracting RP 1 & 7...")
    controller.setSpeed(1, 0)
    controller.setSpeed(7, 0)
    set_rp(1, "retracted", controller)
    set_rp(7, "retracted", controller)
    wait()
    
    print("  Resetting grippers 0 & 6 to B...")
    set_gripper(0, "B", controller)
    set_gripper(6, "B", controller)
    wait()
    
    print("  Engaging RP 1 & 7...")
    controller.setSpeed(1, 50)
    controller.setSpeed(7, 50)
    set_rp(1, "hold", controller)
    set_rp(7, "hold", controller)
    wait()
    
    print("  Retracting RP 3 & 9...")
    controller.setSpeed(3, 0)
    controller.setSpeed(9, 0)
    set_rp(3, "retracted", controller)
    set_rp(9, "retracted", controller)
    wait()


# ─── Main Scan Sequence ─────────────────────────────────────────────────────

def scan_cube(controller, camera):
    """
    Scan all 6 faces and return to White front / Blue top.
    
    Scan order: F(White), B(Yellow), L(Orange), R(Red), D(Green), U(Blue)
    """
    faces = []
    
    # ═══ SETUP ═══
    print("\n═══ SETUP: Moving to starting positions ═══")
    for ch in [0, 2, 6, 8]:
        controller.setAccel(ch, GRIPPER_ACCEL)
    
    set_gripper(0, "B", controller)
    set_gripper(2, "C", controller)
    set_gripper(6, "B", controller)
    set_gripper(8, "A", controller)
    
    for ch in [1, 3, 7, 9]:
        controller.setSpeed(ch, 0)
        set_rp(ch, "retracted", controller)
    wait()
    
    input("\n  ⏳ Insert cube (White front, Blue top), then press Enter...")
    
    # ═══ STEP 1: Engage grippers ═══
    print("\n═══ STEP 1: Engage all 4 RP ═══")
    for ch in [1, 3, 7, 9]:
        controller.setSpeed(ch, 50)
        set_rp(ch, "hold", controller)
    wait()
    
    # ═══ STEP 2: Retract RP 1&7 for Y-axis scanning ═══
    print("\n═══ STEP 2: Retract RP 1 & 7 ═══")
    controller.setSpeed(1, 0)
    controller.setSpeed(7, 0)
    set_rp(1, "retracted", controller)
    set_rp(7, "retracted", controller)
    wait()
    
    # ═══ STEP 3: Scan FRONT (White) ═══
    print("\n═══ STEP 3: Capture FRONT face ═══")
    f = take_photo("front", 1, camera)
    if f: faces.append(("front", f))
    
    # ═══ STEP 4: Y 180° + Scan BACK (Yellow) ═══
    print("\n═══ STEP 4: Y 180° rotation ═══")
    y_rotate_180(controller)
    # Grippers now at A/C
    
    print("\n═══ STEP 5: Capture BACK face ═══")
    f = take_photo("back", 2, camera)
    if f: faces.append(("back", f))
    
    # ═══ STEP 6: Y CW 90° + Scan LEFT (Orange) ═══
    print("\n═══ STEP 6: Reset + Y CW 90° rotation ═══")
    reset_grippers_2_8_to_B(controller)
    y_rotate_cw_90(controller)
    # Grippers now at A/C
    
    print("\n═══ STEP 7: Capture LEFT face ═══")
    f = take_photo("left", 4, camera)
    if f: faces.append(("left", f))
    
    # ═══ STEP 8: Y 180° + Scan RIGHT (Red) ═══
    print("\n═══ STEP 8: Y 180° rotation ═══")
    # From A/C, Y 180° goes to C/A
    controller.setTarget(2, GRIPPER[2]['C'] * 4)
    controller.setTarget(8, GRIPPER[8]['A'] * 4)
    print("  Y 180° rotation (2: A→C, 8: C→A)...")
    wait(SIMULTANEOUS_DELAY)
    
    print("\n═══ STEP 9: Capture RIGHT face ═══")
    f = take_photo("right", 3, camera)
    if f: faces.append(("right", f))
    
    # ═══ STEP 10: Y CW 90° + X forward 90° + Scan BOTTOM (Green) ═══
    print("\n═══ STEP 10: Reset + Y CW 90° ═══")
    reset_grippers_2_8_to_B(controller)
    y_rotate_cw_90(controller)
    # Back to Yellow front (Y total = 180+90+180+90 = 540° = 180° net)
    
    print("\n═══ STEP 11: Prep for X rotation ═══")
    prep_for_x_rotation(controller)
    
    print("\n═══ STEP 12: X forward 90° tumble ═══")
    x_rotate_forward_90(controller)
    # Now Green (D) is front
    
    # Square the cube
    print("  Squaring cube...")
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
    
    print("\n═══ STEP 13: Capture BOTTOM face ═══")
    f = take_photo("bottom", 6, camera)
    if f: faces.append(("bottom", f))
    
    # ═══ STEP 14: X 180° + Scan TOP (Blue) ═══
    print("\n═══ STEP 14: X 180° tumble ═══")
    x_rotate_180(controller)
    # Now Blue (U) is front
    
    # Square the cube
    print("  Squaring cube...")
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
    
    print("\n═══ STEP 15: Capture TOP face ═══")
    f = take_photo("top", 5, camera)
    if f: faces.append(("top", f))
    
    # ═══ STEP 16: Return to start (X backward 90° + Y 180°) ═══
    print("\n═══ STEP 16: Return to original orientation ═══")
    
    # X backward 90° (Blue front → White front on Y axis)
    # First reset 0&6 to B
    reset_grippers_0_6_to_B(controller)
    
    print("  X backward 90° tumble...")
    x_rotate_backward_90(controller)
    # Now: Yellow front, Blue top (X total = 90+180-90 = 180°... wait)
    # Let me recalculate:
    # After step 14: X = 90 (fwd) + 180 = 270° = -90° net
    # After X back 90: X = -90 + 90 = 0° ✓
    # But Y is still +180° net, so Yellow is front
    
    # Y 180° to get White front
    reset_grippers_0_6_to_B(controller)
    
    # Transfer to 3&9 for Y rotation
    print("  Engaging RP 3 & 9...")
    controller.setSpeed(3, 50)
    controller.setSpeed(9, 50)
    set_rp(3, "hold", controller)
    set_rp(9, "hold", controller)
    wait()
    
    print("  Retracting RP 1 & 7...")
    controller.setSpeed(1, 0)
    controller.setSpeed(7, 0)
    set_rp(1, "retracted", controller)
    set_rp(7, "retracted", controller)
    wait()
    
    print("  Y 180° rotation...")
    y_rotate_180(controller)
    # Now: White front, Blue top ✓
    
    print(f"\n═══ SCAN COMPLETE: {len(faces)}/6 faces captured ═══")
    print("\n── Results ──")
    for name, path in faces:
        print(f"  {name}: {path}")
    
    return faces


def reset_to_start(controller, hold_cube=True):
    """Return all servos to starting position."""
    print("\n═══ RESETTING TO START ═══")
    if hold_cube:
        controller.setSpeed(1, 50)
        controller.setSpeed(7, 50)
        set_rp(1, "hold", controller)
        set_rp(7, "hold", controller)
        wait(1.0)
        controller.setSpeed(3, 0)
        controller.setSpeed(9, 0)
        set_rp(3, "retracted", controller)
        set_rp(9, "retracted", controller)
    else:
        for ch in [1, 3, 7, 9]:
            controller.setSpeed(ch, 0)
            set_rp(ch, "retracted", controller)
    wait(1.0)
    for g in [0, 2, 6, 8]:
        set_gripper(g, "B", controller)
    wait()
    print(f"  ✅ Reset complete {'(cube held by 0&6)' if hold_cube else '(all retracted)'}")


# ─── Main ───────────────────────────────────────────────────────────────────

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
        print("\nResetting servos...")
        reset_to_start(controller, hold_cube=True)
    finally:
        camera.release()
        controller.close()
    
    print("Done.")


if __name__ == '__main__':
    main()
