#!/usr/bin/env python3
"""
RCubed Full Pipeline: Scan → return to solve position
RULE: Always hold with at least 2 grippers. Engage new BEFORE releasing old.
"""

import sys
import os
import time
import cv2
import subprocess

sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maestro

SCAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scans")

GRIPPER = {
    0: {"A": 467, "B": 1150, "C": 1806, "D": 2500},
    2: {"A": 432, "B": 1064, "C": 1761, "D": 2415},
    6: {"A": 440, "B": 1075, "C": 1761, "D": 2393},
    8: {"A": 442, "B": 1118, "C": 1771, "D": 2436},
}
RP = {
    1: {"retracted": 1857, "hold": 1080},
    3: {"retracted": 1758, "hold": 1050},
    7: {"retracted": 1692, "hold": 766},
    9: {"retracted": 1856, "hold": 1008},
}

GRIPPER_ACCEL = 110
RP_SLOW = 30

def us(v): return v * 4


def scan_and_return(port='/dev/ttyACM0'):
    subprocess.run(['v4l2-ctl', '-d', '/dev/video0', '-c', 'white_balance_automatic=0'], capture_output=True)
    subprocess.run(['v4l2-ctl', '-d', '/dev/video0', '-c', 'white_balance_temperature=5500'], capture_output=True)
    
    s = maestro.Controller(port)
    for ch in [0, 2, 6, 8]:
        s.setAccel(ch, GRIPPER_ACCEL)
    
    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    time.sleep(2)
    os.makedirs(SCAN_DIR, exist_ok=True)
    
    def photo(name, num):
        time.sleep(0.5)
        for _ in range(5): cam.read()
        ret, frame = cam.read()
        if ret:
            cv2.imwrite(os.path.join(SCAN_DIR, f'face_{num}_{name}.jpg'), frame)
            print(f'  📸 {num}: {name}')
    
    def slow_engage(*rp_servos):
        """Engage one or more RP servos slowly (simultaneously)."""
        for rp in rp_servos:
            s.setSpeed(rp, RP_SLOW)
            s.setTarget(rp, us(RP[rp]["hold"]))
        time.sleep(1.2)
        for rp in rp_servos:
            s.setSpeed(rp, 0)
    
    def retract(*rp_servos):
        """Retract one or more RP servos."""
        for rp in rp_servos:
            s.setTarget(rp, us(RP[rp]["retracted"]))
        time.sleep(0.5)
    
    def transfer_hold(engage_rps, retract_rps):
        """Engage new grippers FIRST, then retract old ones. Never < 2 holding."""
        slow_engage(*engage_rps)
        retract(*retract_rps)
    
    # ══════════════════════════════════════════════════════════════════════
    # SCAN SEQUENCE
    # Start: 0:B, 2:C, 6:B, 8:A, RP 3&9 hold, RP 1&7 retracted
    # Holding: grippers 2&8 via RP 3&9
    # ══════════════════════════════════════════════════════════════════════
    
    # ══════════════════════════════════════════════════════════════════════
    # SET STARTING POSITION
    # Grippers: 0:B, 2:C, 6:B, 8:A (2&8 rotated so fingers are out of camera view)
    # RP: 3&9 hold (slowly), 1&7 retracted
    # ══════════════════════════════════════════════════════════════════════
    
    print('═══ SETTING START POSITION ═══')
    # First retract all RP
    for rp in [1, 3, 7, 9]:
        s.setTarget(rp, us(RP[rp]["retracted"]))
    time.sleep(0.5)
    
    # Set gripper positions
    s.setTarget(0, us(GRIPPER[0]["B"]))
    s.setTarget(2, us(GRIPPER[2]["C"]))
    s.setTarget(6, us(GRIPPER[6]["B"]))
    s.setTarget(8, us(GRIPPER[8]["A"]))
    time.sleep(1.0)
    
    # Slowly engage RP 3&9 (hold cube with grippers 2&8)
    slow_engage(3, 9)
    print('  Start position set: 0:B, 2:C, 6:B, 8:A, RP 3&9 hold')
    
    print('═══ SCANNING ═══')
    
    # Step 2: Front face (2&8 hold, fingers out of view)
    photo('front', 1)
    
    # Step 3: 180° rotation (2:C→A, 8:A→C) — 2&8 still hold
    s.setTarget(2, us(GRIPPER[2]["A"]))
    s.setTarget(8, us(GRIPPER[8]["C"]))
    time.sleep(1.0)
    
    # Step 4: Back face
    photo('back', 2)
    
    # Step 5: 90° turn — need to transfer hold to 0&6, reset 2&8, transfer back, rotate
    # Currently holding: 2&8 (RP 3&9). Need to engage 0&6 first.
    transfer_hold([1, 7], [3, 9])      # engage 0&6 THEN retract 2&8. Now 0&6 hold.
    s.setTarget(2, us(GRIPPER[2]["B"]))  # reset gripper 2 to B
    s.setTarget(8, us(GRIPPER[8]["B"]))  # reset gripper 8 to B
    time.sleep(0.8)
    transfer_hold([3, 9], [1, 7])      # engage 2&8 THEN retract 0&6. Now 2&8 hold.
    s.setTarget(2, us(GRIPPER[2]["A"]))  # rotate 90°
    s.setTarget(8, us(GRIPPER[8]["C"]))
    time.sleep(1.0)
    
    # Step 6: Right face (2&8 hold at A&C)
    photo('right', 3)
    
    # Step 7: 180° (2:A→C, 8:C→A)
    s.setTarget(2, us(GRIPPER[2]["C"]))
    s.setTarget(8, us(GRIPPER[8]["A"]))
    time.sleep(1.0)
    
    # Step 8: Left face
    photo('left', 4)
    
    # Step 9: Prep for tumble — transfer to 0&6, reset 2&8, tumble with 0&6
    transfer_hold([1, 7], [3, 9])      # engage 0&6 THEN retract 2&8
    s.setTarget(2, us(GRIPPER[2]["B"]))
    s.setTarget(8, us(GRIPPER[8]["B"]))
    time.sleep(0.8)
    # Tumble: 0:B→C, 6:B→A (0&6 hold and rotate)
    s.setTarget(0, us(GRIPPER[0]["C"]))
    s.setTarget(6, us(GRIPPER[6]["A"]))
    time.sleep(1.0)
    
    # Step 10: Top face (0&6 hold at C&A)
    photo('top', 5)
    
    # Step 11: 180° tumble (0:C→A, 6:A→C)
    s.setTarget(0, us(GRIPPER[0]["A"]))
    s.setTarget(6, us(GRIPPER[6]["C"]))
    time.sleep(1.0)
    
    # Step 12: Bottom face
    photo('bottom', 6)
    
    print('═══ SCAN COMPLETE ═══')
    
    # ══════════════════════════════════════════════════════════════════════
    # RETURN TO ORIGINAL ORIENTATION
    # Current: 0:A, 6:C, RP 1&7 hold, RP 3&9 retracted, 2:B, 8:B
    # Need to: undo tumble, undo 90° rotation, end at all B, all RP hold
    # ══════════════════════════════════════════════════════════════════════
    
    print('═══ RETURNING TO SOLVE POSITION ═══')
    
    # Undo 180° tumble: 0:A→C, 6:C→A (back to step 10 position)
    s.setTarget(0, us(GRIPPER[0]["C"]))
    s.setTarget(6, us(GRIPPER[6]["A"]))
    time.sleep(1.0)
    
    # Undo tumble: 0:C→B, 6:A→B
    s.setTarget(0, us(GRIPPER[0]["B"]))
    s.setTarget(6, us(GRIPPER[6]["B"]))
    time.sleep(0.8)
    
    # Transfer to 2&8, then undo 90° rotation
    transfer_hold([3, 9], [1, 7])      # engage 2&8 THEN retract 0&6
    
    # Undo 90° y-rotation: net scan was +90° CW, so undo with 90° CCW
    # y_CCW = servo 2 B→C, servo 8 B→A
    s.setTarget(2, us(GRIPPER[2]["C"]))
    s.setTarget(8, us(GRIPPER[8]["A"]))
    time.sleep(1.0)
    
    # Transfer to 0&6, reset 2&8
    transfer_hold([1, 7], [3, 9])      # engage 0&6 THEN retract 2&8
    s.setTarget(2, us(GRIPPER[2]["B"]))
    s.setTarget(8, us(GRIPPER[8]["B"]))
    time.sleep(0.8)
    
    # Final: engage all 4
    slow_engage(3, 9)   # engage 2&8 (0&6 already holding)
    
    print('═══ READY TO SOLVE ═══')
    print('All grippers at B, all RP hold, original orientation.')
    
    cam.release()
    s.close()


if __name__ == "__main__":
    scan_and_return()
