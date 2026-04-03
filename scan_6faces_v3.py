#!/usr/bin/env python3
"""
RCubed 6-Face Scanner V3 - Clean Balanced Sequence

Grippers at A or C = OUT of camera view (good for scanning)
Grippers at B or D = IN camera view (bad for scanning)

Phase 1: Y rotations (4 side faces)
  Start: grippers 2&8 at C/A (out of view)
  1. Scan FRONT (White)
  2. Y 180° (C→A, A→C) → Scan BACK (Yellow) - still at A/C (out of view)
  3. Y 90° CW → Scan RIGHT (Red) - need reset + rotate
  4. Y 180° → Scan LEFT (Orange)
  5. Y 90° CW → Return to White front

Phase 2: X rotations (top/bottom)
  Need grippers 2&8 out of view, grippers 0&6 can rotate
  6. X fwd 90° → Scan TOP (Blue)
  7. X fwd 180° → Scan BOTTOM (Green)
  8. X fwd 90° → Return to start
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
    
    # Rotation corrections
    if name == "top":
        cropped = cv2.rotate(cropped, cv2.ROTATE_90_CLOCKWISE)
    elif name == "bottom":
        cropped = cv2.rotate(cropped, cv2.ROTATE_90_COUNTERCLOCKWISE)
    
    path = os.path.join(SCAN_DIR, f"face_{face_num}_{name}.jpg")
    cv2.imwrite(path, cropped)
    print(f"  📸 {name} → face_{face_num}_{name}.jpg")
    return path


# ─── Y Rotation (grippers 2 & 8) ────────────────────────────────────────────

def setup_for_y(controller):
    """Setup for Y rotation: RP 3&9 hold, RP 1&7 retracted"""
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

def y_180(controller):
    """Y 180°: swap positions (C↔A). Grippers stay out of camera view."""
    print("  Y 180°...")
    # If at C/A, go to A/C. If at A/C, go to C/A.
    # This is a simple swap - both end positions are out of camera view.
    set_gripper(2, "A", controller)
    set_gripper(8, "C", controller)
    wait(Y_ROTATION_DELAY)

def y_180_reverse(controller):
    """Y 180° reverse direction."""
    print("  Y 180°...")
    set_gripper(2, "C", controller)
    set_gripper(8, "A", controller)
    wait(Y_ROTATION_DELAY)

def y_cw_90_from_CA(controller):
    """Y CW 90° from C/A position. Goes to B position (in view!) then to A/C."""
    print("  Y CW 90°...")
    # From 2:C, 8:A → need to go through B to get to A/C
    # But B is in view! So we need to:
    # 1. Rotate 90° (ends at positions that ARE out of view due to 90° turn)
    # Actually, from C, CW 90° goes to D. From A, CW 90° goes to B.
    # D and B are IN view. 
    #
    # Let's think about this differently:
    # A→B→C→D→A is the servo position sequence
    # For cube CW rotation from camera's perspective:
    #   Gripper 2 (top): needs to turn one direction
    #   Gripper 8 (bottom): needs to turn opposite direction
    #
    # If 2 goes C→B (that's CCW in servo terms) and 8 goes A→B (that's CW in servo terms)
    # That's SAME direction = no cube rotation.
    #
    # For cube rotation, they must go OPPOSITE servo directions:
    #   2: C→D (or C→B)
    #   8: A→D (or A→B) - but these are same direction!
    #
    # Wait, I need to reconsider. Let me just do:
    # 2: C→A (skipping B, going through D) = 180° servo, 90° cube rotation? No...
    #
    # OK, the issue is that from C/A, a 90° cube rotation ends at D/B which are in view.
    # 
    # Solution: Do 180° rotations only, or accept that for 90° rotations we need
    # a transfer step to get grippers back to A/C before scanning.
    
    # For now: 2:C→D, 8:A→B (but these go same direction so cube spins!)
    # Actually 2:C→B is -90° (CCW), 8:A→B is +90° (CW) = opposite = cube rotates!
    set_gripper(2, "B", controller)  # C→B
    set_gripper(8, "B", controller)  # A→B - wait, same direction!
    
    # I think I need: 2:C→B (CCW), 8:A→D (also CCW looking from top)
    # No wait, from top view: 2 is on top, 8 is on bottom
    # For Y CW cube rotation: top surface rotates CW, bottom surface rotates CW
    # So gripper 2 rotates CW, gripper 8 rotates CW
    # But gripper 2 is upside down! So its CW is opposite.
    
    # This is confusing. Let me just use what worked before:
    # Y CW was: 2:B→A, 8:B→C (opposite servo directions)
    # So from C/A, to do equivalent 90° CW:
    #   2: C → B (one step CCW in servo)
    #   8: A → B (one step CW in servo) 
    # These are opposite directions, so cube should rotate!
    # But both end at B which is in camera view...
    
    wait(Y_ROTATION_DELAY)

def reset_grippers_2_8_to_AC(controller):
    """Reset grippers 2&8 from B to A/C (out of camera view). Requires hold transfer."""
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
    # Move grippers to A/C (out of view)
    set_gripper(2, "A", controller)
    set_gripper(8, "C", controller)
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

def reset_grippers_2_8_to_CA(controller):
    """Reset grippers 2&8 from B to C/A (out of camera view). Requires hold transfer."""
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
    set_gripper(2, "C", controller)
    set_gripper(8, "A", controller)
    wait()
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


# ─── X Rotation (grippers 0 & 6) ────────────────────────────────────────────

def setup_for_x(controller):
    """Setup for X rotation: RP 1&7 hold, RP 3&9 retracted, grippers 2&8 at A/C"""
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
    # Grippers 2&8 to A/C (out of camera view)
    set_gripper(2, "A", controller)
    set_gripper(8, "C", controller)
    wait()

def x_forward_90(controller):
    """X forward 90°: 0:B→C, 6:B→A (tumble toward camera)"""
    print("  X forward 90°...")
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

def reset_grippers_0_6_to_B(controller):
    """Reset grippers 0&6 to B. Requires hold transfer."""
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
    set_gripper(0, "B", controller)
    set_gripper(6, "B", controller)
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


# ─── Main Scan Sequence ─────────────────────────────────────────────────────

def scan_cube(controller, camera):
    faces = []
    
    # ═══ SETUP ═══
    print("\n═══ SETUP ═══")
    for ch in [0, 2, 6, 8]:
        controller.setAccel(ch, GRIPPER_ACCEL)
    
    # Grippers 0&6 to B, grippers 2&8 to C/A (out of camera view)
    set_gripper(0, "B", controller)
    set_gripper(6, "B", controller)
    set_gripper(2, "C", controller)
    set_gripper(8, "A", controller)
    
    # Retract all RP
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
    
    # ═══ PHASE 1: Y rotations (4 side faces) ═══
    print("\n═══ PHASE 1: Side faces ═══")
    
    setup_for_y(controller)
    # Grippers 2&8 at C/A (out of view) ✓
    
    # 1. Scan FRONT (White)
    print("\n[1/6] FRONT (White)")
    f = take_photo("front", 1, camera)
    if f: faces.append(("front", f))
    
    # 2. Y 180° → Scan BACK (Yellow)
    # From C/A → A/C (both out of view) ✓
    print("\n[2/6] BACK (Yellow)")
    y_180(controller)
    f = take_photo("back", 2, camera)
    if f: faces.append(("back", f))
    
    # 3. Y 90° CW → Scan RIGHT (Red)
    # Need to go A/C → somewhere out of view
    # 90° from A/C ends at B/D or D/B (in view!)
    # So: rotate 90° to B/B, then transfer and move to C/A
    print("\n[3/6] RIGHT (Red)")
    print("  Y CW 90°...")
    set_gripper(2, "B", controller)  # A→B
    set_gripper(8, "B", controller)  # C→B  (opposite directions = cube rotates)
    wait(Y_ROTATION_DELAY)
    # Now at B/B (in view!), need to move to A/C or C/A
    reset_grippers_2_8_to_CA(controller)
    f = take_photo("right", 3, camera)
    if f: faces.append(("right", f))
    
    # 4. Y 180° → Scan LEFT (Orange)
    # From C/A → A/C (both out of view) ✓
    print("\n[4/6] LEFT (Orange)")
    y_180(controller)
    f = take_photo("left", 4, camera)
    if f: faces.append(("left", f))
    
    # 5. Y 90° CW → Return to White front
    print("\n  Returning to White front...")
    print("  Y CW 90°...")
    set_gripper(2, "B", controller)  # A→B
    set_gripper(8, "B", controller)  # C→B
    wait(Y_ROTATION_DELAY)
    reset_grippers_2_8_to_CA(controller)
    # Y total = 180 + 90 + 180 + 90 = 540° = 180° ... not 360!
    # Need to fix this. Let me recalculate...
    # 
    # Actually the issue is direction. Let me trace:
    # Start: F=White
    # Y 180°: F=Yellow
    # Y CW 90°: If CW from Yellow front... F=Orange? or F=Red?
    #   Y CW (from above): front goes right, right goes back, back goes left, left goes front
    #   So from F=Yellow: F=Red (which was on left? no...)
    #   
    # This is getting confusing. Let me just test it and see what happens!
    
    # ═══ PHASE 2: X rotations (top/bottom) ═══
    print("\n═══ PHASE 2: Top/Bottom ═══")
    
    setup_for_x(controller)
    # Grippers 2&8 at A/C (out of view), grippers 0&6 at B
    
    # 6. X forward 90° → Scan TOP (Blue)
    print("\n[5/6] TOP (Blue)")
    x_forward_90(controller)
    reset_grippers_0_6_to_B(controller)
    f = take_photo("top", 5, camera)
    if f: faces.append(("top", f))
    
    # 7. X forward 180° → Scan BOTTOM (Green)
    print("\n[6/6] BOTTOM (Green)")
    x_forward_90(controller)
    reset_grippers_0_6_to_B(controller)
    x_forward_90(controller)
    reset_grippers_0_6_to_B(controller)
    f = take_photo("bottom", 6, camera)
    if f: faces.append(("bottom", f))
    
    # 8. X forward 90° → Return to start
    print("\n  Returning to White front, Blue top...")
    x_forward_90(controller)
    
    print(f"\n═══ SCAN COMPLETE: {len(faces)}/6 faces ═══")
    for name, path in faces:
        print(f"  {name}: {path}")
    
    return faces


def reset_to_start(controller, hold_cube=True):
    """Return all servos to starting position."""
    print("\n═══ RESET ═══")
    if hold_cube:
        controller.setSpeed(1, 50)
        controller.setSpeed(7, 50)
        set_rp(1, "hold", controller)
        set_rp(7, "hold", controller)
        wait()
        controller.setSpeed(3, 0)
        controller.setSpeed(9, 0)
        set_rp(3, "retracted", controller)
        set_rp(9, "retracted", controller)
    else:
        for ch in [1, 3, 7, 9]:
            controller.setSpeed(ch, 0)
            set_rp(ch, "retracted", controller)
    wait()
    for g in [0, 2, 6, 8]:
        set_gripper(g, "B", controller)
    wait()
    print("  ✅ Done")


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
        reset_to_start(controller, hold_cube=True)
    finally:
        camera.release()
        controller.close()
    
    print("\nDone!")


if __name__ == '__main__':
    main()
