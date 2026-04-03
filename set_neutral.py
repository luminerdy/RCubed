#!/usr/bin/env python3
"""
Set all servos to center position (6000) for gripper attachment
"""
import sys
sys.path.insert(0, '/home/luminerdy/rcubed')

import maestro
import time

# Connect to Maestro
try:
    controller = maestro.Controller('/dev/ttyACM0')
    print("✅ Connected to Maestro")
except:
    controller = maestro.Controller('/dev/ttyACM1')
    print("✅ Connected to Maestro on ACM1")

# Set all active servos to center (6000)
servos = [0, 1, 2, 3, 6, 7, 8, 9]

print("\n🔄 Setting all servos to center position (6000)...")

for servo in servos:
    controller.setTarget(servo, 6000)
    print(f"  Servo {servo}: 6000")
    time.sleep(0.2)

print("\n✅ All servos at center position!")
print("\nYou can now attach and tighten the grippers.")
print("The servo shafts are all in the same neutral position (6000).\n")

controller.close()
