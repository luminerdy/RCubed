#!/usr/bin/env python3
"""
Fix return: X forward 180° to get White front / Blue top.
Current: Green front (D), Yellow top (B)
After X 180°: White front (F), Blue top (U)
"""
import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maestro

with open('servo_config.json') as f:
    config = json.load(f)
    GRIPPER = {int(k): v for k, v in config['gripper'].items()}
    RP = {int(k): v for k, v in config['rp'].items()}

def main():
    ctrl = maestro.Controller('/dev/ttyACM0')
    
    for ch in [0, 2, 6, 8]:
        ctrl.setAccel(ch, 110)
    
    print("Current: Green front (D), Yellow top (B)")
    print("Target: White front (F), Blue top (U)")
    print("Solution: X forward 180°")
    print()
    
    # Engage RP 1&7 for X rotation
    print("Engaging RP 1 & 7...")
    ctrl.setSpeed(1, 50)
    ctrl.setSpeed(7, 50)
    ctrl.setTarget(1, RP[1]['hold'] * 4)
    ctrl.setTarget(7, RP[7]['hold'] * 4)
    time.sleep(1.5)
    
    # Retract RP 3&9
    print("Retracting RP 3 & 9...")
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    ctrl.setTarget(3, RP[3]['retracted'] * 4)
    ctrl.setTarget(9, RP[9]['retracted'] * 4)
    time.sleep(2)
    
    # Grippers 2&8 to B (out of the way)
    print("Moving grippers 2 & 8 to B...")
    ctrl.setTarget(2, GRIPPER[2]['B'] * 4)
    ctrl.setTarget(8, GRIPPER[8]['B'] * 4)
    time.sleep(1.5)
    
    # X forward 180°: 0:B→D, 6:B→D (same direction = no rotation)
    # Wait, for X rotation grippers move OPPOSITE
    # X forward: 0:B→C, 6:B→A (90°)
    # Then 0:C→A, 6:A→C (another 90° = 180° total)
    
    print("X forward 90° (0:B→C, 6:B→A)...")
    ctrl.setSpeed(0, 60)
    ctrl.setSpeed(6, 45)
    ctrl.setTarget(0, GRIPPER[0]['C'] * 4)
    ctrl.setTarget(6, GRIPPER[6]['A'] * 4)
    time.sleep(2.5)
    
    print("X forward another 90° (0:C→A, 6:A→C)...")
    ctrl.setTarget(0, GRIPPER[0]['A'] * 4)
    ctrl.setTarget(6, GRIPPER[6]['C'] * 4)
    time.sleep(2.5)
    ctrl.setSpeed(0, 0)
    ctrl.setSpeed(6, 0)
    
    print("\n✅ Done! Check orientation - should be White front, Blue top")
    ctrl.close()

if __name__ == '__main__':
    main()
