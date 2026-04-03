#!/usr/bin/env python3
"""
Simple script to open grippers for cube loading.
No tests, just sets load position.
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
    print("Connecting to Maestro...")
    ctrl = maestro.Controller('/dev/ttyACM0')
    
    # Set acceleration
    for ch in [0, 2, 6, 8]:
        ctrl.setAccel(ch, 110)
    
    # Retract all RP servos (fast)
    print("Retracting all RP servos...")
    for ch in [1, 3, 7, 9]:
        ctrl.setSpeed(ch, 0)
        ctrl.setTarget(ch, RP[ch]['retracted'] * 4)
    time.sleep(2.0)
    
    # Set load positions
    print("Setting load position...")
    ctrl.setTarget(0, GRIPPER[0]['B'] * 4)
    ctrl.setTarget(6, GRIPPER[6]['B'] * 4)
    ctrl.setTarget(2, GRIPPER[2]['C'] * 4)
    ctrl.setTarget(8, GRIPPER[8]['A'] * 4)
    time.sleep(1.0)
    
    print("\n✅ READY TO LOAD CUBE")
    print("   Position: White front (F), Blue top (U)")
    print("   Grippers: 0&6 at B, 2 at C, 8 at A")
    print("   All RP: retracted")
    
    ctrl.close()

if __name__ == '__main__':
    main()
