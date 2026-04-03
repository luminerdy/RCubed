#!/usr/bin/env python3
"""
Final fix: Y 180° to flip Yellow→White.
Current: Yellow front, Blue top
Target: White front, Blue top
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
    
    print("Current: Yellow front, Blue top")
    print("Target: White front, Blue top")
    print("Solution: Y 180°")
    print()
    
    # Engage RP 3&9 for Y rotation
    print("Engaging RP 3 & 9...")
    ctrl.setSpeed(3, 50)
    ctrl.setSpeed(9, 50)
    ctrl.setTarget(3, RP[3]['hold'] * 4)
    ctrl.setTarget(9, RP[9]['hold'] * 4)
    time.sleep(1.5)
    
    # Retract RP 1&7
    print("Retracting RP 1 & 7...")
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    ctrl.setTarget(1, RP[1]['retracted'] * 4)
    ctrl.setTarget(7, RP[7]['retracted'] * 4)
    time.sleep(2)
    
    # Grippers 0&6 to B
    print("Moving grippers 0 & 6 to B...")
    ctrl.setTarget(0, GRIPPER[0]['B'] * 4)
    ctrl.setTarget(6, GRIPPER[6]['B'] * 4)
    time.sleep(1.5)
    
    # Y 180°: two 90° rotations
    # Y CW 90°: 2:B→A, 8:B→C
    print("Y CW 90° (1 of 2)...")
    ctrl.setTarget(2, GRIPPER[2]['A'] * 4)
    ctrl.setTarget(8, GRIPPER[8]['C'] * 4)
    time.sleep(2)
    
    # Reset to B
    print("Resetting 2&8 to B...")
    ctrl.setSpeed(1, 50)
    ctrl.setSpeed(7, 50)
    ctrl.setTarget(1, RP[1]['hold'] * 4)
    ctrl.setTarget(7, RP[7]['hold'] * 4)
    time.sleep(1.5)
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    ctrl.setTarget(3, RP[3]['retracted'] * 4)
    ctrl.setTarget(9, RP[9]['retracted'] * 4)
    time.sleep(2)
    ctrl.setTarget(2, GRIPPER[2]['B'] * 4)
    ctrl.setTarget(8, GRIPPER[8]['B'] * 4)
    time.sleep(1.5)
    
    # Transfer back
    ctrl.setSpeed(3, 50)
    ctrl.setSpeed(9, 50)
    ctrl.setTarget(3, RP[3]['hold'] * 4)
    ctrl.setTarget(9, RP[9]['hold'] * 4)
    time.sleep(1.5)
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    ctrl.setTarget(1, RP[1]['retracted'] * 4)
    ctrl.setTarget(7, RP[7]['retracted'] * 4)
    time.sleep(2)
    
    # Y CW 90° again
    print("Y CW 90° (2 of 2)...")
    ctrl.setTarget(2, GRIPPER[2]['A'] * 4)
    ctrl.setTarget(8, GRIPPER[8]['C'] * 4)
    time.sleep(2)
    
    print("\n✅ Should now be White front, Blue top!")
    ctrl.close()

if __name__ == '__main__':
    main()
