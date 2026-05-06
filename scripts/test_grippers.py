#!/usr/bin/env python3
"""
RCubed - Load Cube Position
Sets servos to the load position for inserting a cube.

Load position:
  - Grippers 0 & 6: B (fingers horizontal, cube fits between)
  - Grippers 2 & 8: A (fingers out of the way)
  - All RP: retracted (away from cube)
"""

import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
import maestro
import robot_state

# Servo calibration values (updated 2026-03-07)
GRIPPER = {
    0: {"A": 400, "B": 1100, "C": 1785, "D": 2420},
    2: {"A": 400, "B": 1040, "C": 1710, "D": 2400},
    6: {"A": 475, "B": 1120, "C": 1800, "D": 2425},
    8: {"A": 450, "B": 1120, "C": 1810, "D": 2425},
}

RP = {
    1: {"retracted": 1890, "hold": 1055},
    3: {"retracted": 1815, "hold": 1100},
    7: {"retracted": 1875, "hold": 990},
    9: {"retracted": 1880, "hold": 1100},
}

GRIPPER_ACCEL = 110

def main():
    # Invalidate state up front — we're about to move everything
    # and will save a fresh clean state at the end
    robot_state.invalidate()

    print("Connecting to Maestro...")
    ctrl = maestro.Controller('/dev/ttyACM0')
    
    # Set gripper acceleration
    for ch in [0, 2, 6, 8]:
        ctrl.setAccel(ch, GRIPPER_ACCEL)
    
    # Safety: retract all RP first
    print("\n═══ SAFETY: RETRACTING ALL RP SERVOS ═══")
    for rp in [1, 3, 7, 9]:
        ctrl.setSpeed(rp, 0)  # fast
        ctrl.setTarget(rp, RP[rp]['retracted'] * 4)
    time.sleep(1.5)
    
    # Set all grippers to neutral position B
    print("\n═══ SAFETY: SETTING ALL GRIPPERS TO NEUTRAL (B) ═══")
    for servo in [0, 2, 6, 8]:
        ctrl.setTarget(servo, GRIPPER[servo]['B'] * 4)
    time.sleep(1.5)
    
    print("\n═══ TESTING GRIPPER SERVOS ═══")
    
    # Test servo 0: D → B
    print("  Testing servo 0 (left): D → B")
    ctrl.setTarget(0, GRIPPER[0]['D'] * 4)
    time.sleep(1.0)
    ctrl.setTarget(0, GRIPPER[0]['B'] * 4)
    time.sleep(1.0)
    
    # Test servo 6: D → B
    print("  Testing servo 6 (right): D → B")
    ctrl.setTarget(6, GRIPPER[6]['D'] * 4)
    time.sleep(1.0)
    ctrl.setTarget(6, GRIPPER[6]['B'] * 4)
    time.sleep(1.0)
    
    # Test servo 2: A → C (stays at C)
    print("  Testing servo 2 (top): A → C")
    ctrl.setTarget(2, GRIPPER[2]['A'] * 4)
    time.sleep(1.0)
    ctrl.setTarget(2, GRIPPER[2]['C'] * 4)
    time.sleep(1.0)
    
    # Test servo 8: C → A (stays at A)
    print("  Testing servo 8 (bottom): C → A")
    ctrl.setTarget(8, GRIPPER[8]['C'] * 4)
    time.sleep(1.0)
    ctrl.setTarget(8, GRIPPER[8]['A'] * 4)
    time.sleep(1.0)
    
    # Set all grippers to B for rotation tests
    print("\n═══ ROTATION TESTS ═══")
    print("  Setting all grippers to B...")
    for servo in [0, 2, 6, 8]:
        ctrl.setTarget(servo, GRIPPER[servo]['B'] * 4)
    time.sleep(1.5)
    
    # Engage all RP servos
    print("  Engaging all RP servos...")
    for rp in [1, 3, 7, 9]:
        ctrl.setSpeed(rp, 30)  # slow engage
        ctrl.setTarget(rp, RP[rp]['hold'] * 4)
    time.sleep(2.0)
    
    # Test Y rotation (2 & 8) - retract 1 & 7 for clearance
    print("  Retracting RP 1 & 7 for Y rotation...")
    ctrl.setSpeed(1, 0)
    ctrl.setSpeed(7, 0)
    ctrl.setTarget(1, RP[1]['retracted'] * 4)
    ctrl.setTarget(7, RP[7]['retracted'] * 4)
    time.sleep(1.5)
    
    print("  Testing Y rotation CW (2:B→A, 8:B→C)...")
    ctrl.setTarget(2, GRIPPER[2]['A'] * 4)
    ctrl.setTarget(8, GRIPPER[8]['C'] * 4)
    time.sleep(2.0)
    print("  Returning Y rotation (2:A→B, 8:C→B)...")
    ctrl.setTarget(2, GRIPPER[2]['B'] * 4)
    ctrl.setTarget(8, GRIPPER[8]['B'] * 4)
    time.sleep(2.0)
    
    # Re-engage 1 & 7, retract 3 & 9 for X rotation
    print("  Re-engaging RP 1 & 7...")
    ctrl.setSpeed(1, 30)
    ctrl.setSpeed(7, 30)
    ctrl.setTarget(1, RP[1]['hold'] * 4)
    ctrl.setTarget(7, RP[7]['hold'] * 4)
    time.sleep(1.5)
    
    print("  Retracting RP 3 & 9 for X rotation...")
    ctrl.setSpeed(3, 0)
    ctrl.setSpeed(9, 0)
    ctrl.setTarget(3, RP[3]['retracted'] * 4)
    ctrl.setTarget(9, RP[9]['retracted'] * 4)
    time.sleep(1.5)
    
    print("  Testing X rotation forward (0:B→C, 6:B→A)...")
    ctrl.setSpeed(0, 60)  # current speed
    ctrl.setSpeed(6, 45)  # faster (lower = faster)
    ctrl.setTarget(0, GRIPPER[0]['C'] * 4)
    ctrl.setTarget(6, GRIPPER[6]['A'] * 4)
    time.sleep(2.5)  # slower for X
    print("  Returning X rotation (0:C→B, 6:A→B)...")
    ctrl.setTarget(0, GRIPPER[0]['B'] * 4)
    ctrl.setTarget(6, GRIPPER[6]['B'] * 4)
    time.sleep(2.5)
    
    # Retract all RP servos
    print("  Retracting all RP servos...")
    for rp in [1, 3, 7, 9]:
        ctrl.setSpeed(rp, 0)  # fast
        ctrl.setTarget(rp, RP[rp]['retracted'] * 4)
    time.sleep(2.0)
    
    # Set grippers to load positions
    print("  Setting load positions...")
    ctrl.setTarget(0, GRIPPER[0]['B'] * 4)
    ctrl.setTarget(6, GRIPPER[6]['B'] * 4)
    ctrl.setTarget(2, GRIPPER[2]['C'] * 4)
    ctrl.setTarget(8, GRIPPER[8]['A'] * 4)
    time.sleep(1.5)
    
    print("\n✅ READY TO LOAD CUBE")
    print("   Position: White front (F), Blue top (U)")
    print("   Grippers: 0&6 at B, 2 at C, 8 at A")
    print("   All RP: retracted")

    # Save clean state — grippers end at load position, all RPs retracted
    robot_state.save(
        gripper_pos={0: 'B', 2: 'C', 6: 'B', 8: 'A'},
        rp_status={1: 'retracted', 3: 'retracted', 7: 'retracted', 9: 'retracted'},
    )

    ctrl.close()

if __name__ == "__main__":
    main()
