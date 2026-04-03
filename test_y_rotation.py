#!/usr/bin/env python3
"""
Test Y rotation step by step to debug what's happening.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maestro
import json

with open('servo_config.json') as f:
    config = json.load(f)
    GRIPPER = {int(k): v for k, v in config['gripper'].items()}
    RP = {int(k): v for k, v in config['rp'].items()}

def main():
    ctrl = maestro.Controller('/dev/ttyACM0')
    
    # Set acceleration
    for ch in [0, 2, 6, 8]:
        ctrl.setAccel(ch, 110)
    
    print("Y Rotation Test")
    print("="*50)
    print("\nStarting with all grippers at B, RP 3&9 holding")
    
    # Start position - all at B
    for g in [0, 2, 6, 8]:
        ctrl.setTarget(g, GRIPPER[g]['B'] * 4)
    time.sleep(1)
    
    # RP 3&9 hold (for Y rotation, these hold while 2&8 rotate)
    ctrl.setSpeed(3, 50)
    ctrl.setSpeed(9, 50)
    ctrl.setTarget(3, RP[3]['hold'] * 4)
    ctrl.setTarget(9, RP[9]['hold'] * 4)
    time.sleep(1.5)
    
    # RP 1&7 retract
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    ctrl.setTarget(1, RP[1]['retracted'] * 4)
    ctrl.setTarget(7, RP[7]['retracted'] * 4)
    time.sleep(2)
    
    input("\nPress Enter to do Y CW rotation (2:B→A, 8:B→C)...")
    
    print("  Gripper 2: B→A")
    print("  Gripper 8: B→C")
    print("  (These should move in OPPOSITE directions)")
    
    ctrl.setTarget(2, GRIPPER[2]['A'] * 4)
    ctrl.setTarget(8, GRIPPER[8]['C'] * 4)
    time.sleep(2)
    
    print("\nDid the cube rotate? (Y/N)")
    result = input().strip().upper()
    
    if result == 'N':
        print("\n>>> PROBLEM: Grippers 2&8 may be moving same direction!")
        print(">>> Check servo_config.json calibration for 2 and 8")
    else:
        print("\n>>> Good! Y rotation works.")
    
    print("\nReturning to B...")
    ctrl.setTarget(2, GRIPPER[2]['B'] * 4)
    ctrl.setTarget(8, GRIPPER[8]['B'] * 4)
    time.sleep(2)
    
    # Re-engage 1&7
    ctrl.setSpeed(1, 50)
    ctrl.setSpeed(7, 50)
    ctrl.setTarget(1, RP[1]['hold'] * 4)
    ctrl.setTarget(7, RP[7]['hold'] * 4)
    time.sleep(1.5)
    
    # Retract 3&9
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    ctrl.setTarget(3, RP[3]['retracted'] * 4)
    ctrl.setTarget(9, RP[9]['retracted'] * 4)
    time.sleep(2)
    
    ctrl.close()
    print("Done.")

if __name__ == '__main__':
    main()
