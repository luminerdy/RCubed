#!/usr/bin/env python3
"""
Final fix: X backward 90° to get Blue to top.
Current: White front, Green top
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
    
    print("Current: White front, Green top")
    print("Target: White front, Blue top")
    print("Solution: X backward 90°")
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
    
    # Grippers 2&8 to B
    print("Moving grippers 2 & 8 to B...")
    ctrl.setTarget(2, GRIPPER[2]['B'] * 4)
    ctrl.setTarget(8, GRIPPER[8]['B'] * 4)
    time.sleep(1.5)
    
    # X backward 90°: 0:B→A, 6:B→C
    print("X backward 90°...")
    ctrl.setSpeed(0, 60)
    ctrl.setSpeed(6, 45)
    ctrl.setTarget(0, GRIPPER[0]['A'] * 4)
    ctrl.setTarget(6, GRIPPER[6]['C'] * 4)
    time.sleep(2.5)
    ctrl.setSpeed(0, 0)
    ctrl.setSpeed(6, 0)
    
    print("\n✅ Should now be White front, Blue top!")
    ctrl.close()

if __name__ == '__main__':
    main()
