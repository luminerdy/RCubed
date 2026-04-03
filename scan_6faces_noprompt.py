#!/usr/bin/env python3
"""
RCubed 6-Face Scanning Sequence
Captures all 6 faces of the Rubik's Cube for color detection.

Servo layout:
  Gripper servos (rotate cube/turn face): 0(left), 2(top), 6(right), 8(bottom)
  RP servos (hold/retract): 1(left), 3(top), 7(right), 9(bottom)

Gripper positions A,B,C,D (~90° apart, A→D is CCW from cube's perspective)
  A and C = camera clear, B and D = camera blocked

All values in microseconds. Maestro library uses quarter-microseconds (×4).
"""

import sys
import os
import time
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maestro

# ─── Servo Calibration ─────────────────────────────────────────────────────

GRIPPER = {
    0: {"A": 467, "B": 1150, "C": 1806, "D": 2500},   # left
    2: {"A": 432, "B": 1064, "C": 1761, "D": 2415},   # top
    6: {"A": 440, "B": 1075, "C": 1761, "D": 2393},   # right
    8: {"A": 442, "B": 1118, "C": 1771, "D": 2436},   # bottom
}

RP = {
    1: {"retracted": 1857, "hold": 1100},   # left
    3: {"retracted": 1758, "hold": 1050},   # top
    7: {"retracted": 1692, "hold": 786},    # right
    9: {"retracted": 1856, "hold": 1008},   # bottom
}

# Gripper servo acceleration (from OTVINTA recommendation)
GRIPPER_ACCEL = 110

# RP servo speed for slow engagement
RP_SLOW_SPEED = 30
RP_NORMAL_SPEED = 0  # unrestricted

# Timing
MOVE_DELAY = 0.8        # seconds to wait after a servo move
SLOW_ENGAGE_DELAY = 1.5 # seconds for slow RP engagement
PHOTO_DELAY = 0.5       # settle time before taking photo
SIMULTANEOUS_DELAY = 1.0 # time for simultaneous 180° moves

# ─── Output directory ───────────────────────────────────────────────────────

SCAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scans")

# ─── Helper Functions ───────────────────────────────────────────────────────

def us_to_qus(us):
    """Convert microseconds to quarter-microseconds for Maestro."""
    return us * 4


def set_gripper(servo, pos, controller):
    """Set a gripper servo to position A/B/C/D."""
    target = us_to_qus(GRIPPER[servo][pos])
    controller.setTarget(servo, target)
    print(f"  Gripper {servo} → {pos} ({GRIPPER[servo][pos]} μs)")


def set_rp(servo, pos, controller):
    """Set an RP servo to 'retracted' or 'hold'."""
    target = us_to_qus(RP[servo][pos])
    controller.setTarget(servo, target)
    print(f"  RP {servo} → {pos} ({RP[servo][pos]} μs)")


def set_rp_slow(servo, pos, controller):
    """Set RP servo slowly (for initial cube engagement)."""
    controller.setSpeed(servo, RP_SLOW_SPEED)
    set_rp(servo, pos, controller)
    time.sleep(SLOW_ENGAGE_DELAY)
    controller.setSpeed(servo, RP_NORMAL_SPEED)


def wait(seconds=None):
    """Wait for servos to reach position."""
    time.sleep(seconds or MOVE_DELAY)


def take_photo(face_name, face_number, camera):
    """Capture an image from the camera."""
    # Let camera auto-adjust
    time.sleep(PHOTO_DELAY)
    # Grab a few frames to flush buffer
    for _ in range(5):
        camera.read()
    ret, frame = camera.read()
    if ret:
        filename = os.path.join(SCAN_DIR, f"face_{face_number}_{face_name}.jpg")
        cv2.imwrite(filename, frame)
        print(f"  📸 Face {face_number}: {face_name} → {filename}")
        return filename
    else:
        print(f"  ❌ Failed to capture face {face_number}: {face_name}")
        return None


# ─── Scanning Sequence ──────────────────────────────────────────────────────

def scan_all_faces(controller, camera):
    """
    Execute the 6-face scanning sequence.
    
    Starting position:
      Gripper 0: B, Gripper 2: C, Gripper 6: B, Gripper 8: A
      All RP: retracted
    
    Returns list of (face_name, filepath) tuples.
    """
    faces = []
    
    # ── Setup: Starting positions ──
    print("\n═══ SETUP: Moving to starting positions ═══")
    set_gripper(0, "B", controller)
    set_gripper(2, "C", controller)
    set_gripper(6, "B", controller)
    set_gripper(8, "A", controller)
    for rp in [1, 3, 7, 9]:
        set_rp(rp, "retracted", controller)
    wait(1.0)
    
    print("\n  ⏳ Insert cube now, then press Enter...")
    # input() skipped
    
    # ── Step 1: Raise cube to center ──
    print("\n═══ STEP 1: Engage grippers 2 & 8 (slow) ═══")
    set_rp_slow(3, "hold", controller)
    set_rp_slow(9, "hold", controller)
    
    # ── Step 2: Front face ──
    print("\n═══ STEP 2: Capture FRONT face ═══")
    f = take_photo("front", 1, camera)
    if f: faces.append(("front", f))
    
    # ── Step 3: 180° rotation to show back face ──
    print("\n═══ STEP 3: 180° rotation (2: C→A, 8: A→C) ═══")
    set_gripper(2, "A", controller)
    set_gripper(8, "C", controller)
    wait(SIMULTANEOUS_DELAY)
    
    # ── Step 4: Back face ──
    print("\n═══ STEP 4: Capture BACK face ═══")
    f = take_photo("back", 2, camera)
    if f: faces.append(("back", f))
    
    # ── Step 5: 90° turn to show right side ──
    print("\n═══ STEP 5: 90° cube rotation ═══")
    # Engage 0 & 6
    print("  Engaging RP 1 & 7...")
    set_rp(1, "hold", controller)
    set_rp(7, "hold", controller)
    wait()
    
    # Retract 2 & 8
    print("  Retracting RP 3 & 9...")
    set_rp(3, "retracted", controller)
    set_rp(9, "retracted", controller)
    wait()
    
    # Reset 2 & 8 to B (neutral, ready for rotation)
    print("  Resetting grippers 2 & 8 to B...")
    set_gripper(2, "B", controller)
    set_gripper(8, "B", controller)
    wait()
    
    # Re-engage 2 & 8
    print("  Re-engaging RP 3 & 9...")
    set_rp(3, "hold", controller)
    set_rp(9, "hold", controller)
    wait()
    
    # Release 0 & 6
    print("  Retracting RP 1 & 7...")
    set_rp(1, "retracted", controller)
    set_rp(7, "retracted", controller)
    wait()
    
    # Rotate cube 90°: 2 B→A, 8 B→C (opposite directions)
    print("  Rotating cube 90° (2: B→A, 8: B→C)...")
    set_gripper(2, "A", controller)
    set_gripper(8, "C", controller)
    wait(SIMULTANEOUS_DELAY)
    
    # NOTE: RP 1 & 7 stay retracted so 0 & 6 don't interfere with step 7's 180° rotation
    
    # ── Step 6: Right face ──
    print("\n═══ STEP 6: Capture RIGHT face ═══")
    f = take_photo("right", 3, camera)
    if f: faces.append(("right", f))
    
    # ── Step 7: 180° rotation to show left side ──
    print("\n═══ STEP 7: 180° rotation (2: A→C, 8: C→A) ═══")
    set_gripper(2, "C", controller)
    set_gripper(8, "A", controller)
    wait(SIMULTANEOUS_DELAY)
    
    # ── Step 8: Left face ──
    print("\n═══ STEP 8: Capture LEFT face ═══")
    f = take_photo("left", 4, camera)
    if f: faces.append(("left", f))
    
    # ── Step 9: Prep for vertical tumble ──
    print("\n═══ STEP 9: Prep for top/bottom scan ═══")
    # Engage 0 & 6
    print("  Engaging RP 1 & 7...")
    set_rp(1, "hold", controller)
    set_rp(7, "hold", controller)
    wait()
    
    # Retract 2 & 8
    print("  Retracting RP 3 & 9...")
    set_rp(3, "retracted", controller)
    set_rp(9, "retracted", controller)
    wait()
    
    # Move 2 & 8 to B (out of the way for 0&6 rotation)
    print("  Moving grippers 2 & 8 to B (clear path for 0&6)...")
    set_gripper(2, "B", controller)
    set_gripper(8, "B", controller)
    wait()
    
    # Tumble cube 90° with 0 & 6: 0 B→C, 6 B→A (opposite)
    print("  Tumbling cube 90° (0: B→C, 6: B→A)...")
    set_gripper(0, "C", controller)
    set_gripper(6, "A", controller)
    wait(SIMULTANEOUS_DELAY)
    
    # ── Step 10: Top face ──
    print("\n═══ STEP 10: Capture TOP face ═══")
    f = take_photo("top", 5, camera)
    if f: faces.append(("top", f))
    
    # ── Step 11: 180° tumble for bottom face ──
    print("\n═══ STEP 11: 180° tumble (0: C→A, 6: A→C) ═══")
    set_gripper(0, "A", controller)
    set_gripper(6, "C", controller)
    wait(SIMULTANEOUS_DELAY)
    
    # ── Step 12: Bottom face ──
    print("\n═══ STEP 12: Capture BOTTOM face ═══")
    f = take_photo("bottom", 6, camera)
    if f: faces.append(("bottom", f))
    
    print(f"\n═══ SCAN COMPLETE: {len(faces)}/6 faces captured ═══")
    return faces


def reset_to_start(controller, hold_cube=True):
    """Return all servos to starting position."""
    print("\n═══ RESETTING TO START ═══")
    # Retract RP 3 & 9
    set_rp(3, "retracted", controller)
    set_rp(9, "retracted", controller)
    if hold_cube:
        # Keep 1 & 7 holding the cube
        set_rp(1, "hold", controller)
        set_rp(7, "hold", controller)
    else:
        set_rp(1, "retracted", controller)
        set_rp(7, "retracted", controller)
    wait(1.0)
    # Set grippers to B (neutral)
    for g in [0, 2, 6, 8]:
        set_gripper(g, "B", controller)
    wait()
    print(f"  ✅ Reset complete {'(cube held by 0&6)' if hold_cube else '(all retracted)'}")


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    # Create scan output directory
    os.makedirs(SCAN_DIR, exist_ok=True)
    
    # Initialize servo controller
    print("Connecting to Maestro...")
    controller = maestro.Controller()
    
    # Set gripper servo acceleration
    for ch in [0, 2, 6, 8]:
        controller.setAccel(ch, GRIPPER_ACCEL)
    
    # Initialize camera
    print("Opening camera...")
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    time.sleep(1)  # let camera warm up
    
    ret, _ = camera.read()
    if not ret:
        print("❌ Camera failed to open!")
        controller.close()
        return
    print("✅ Camera ready")
    
    try:
        faces = scan_all_faces(controller, camera)
        
        print("\n── Results ──")
        for name, path in faces:
            print(f"  {name}: {path}")
        
        print("\nResetting servos...")
        reset_to_start(controller)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted! Resetting servos...")
        reset_to_start(controller)
    finally:
        camera.release()
        controller.close()
        print("Done.")


if __name__ == "__main__":
    main()
