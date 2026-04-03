#!/usr/bin/env python3
"""
Test the 4 gripper TURN servos with BIG movements
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

# TURN servos (grippers)
turn_servos = [0, 2, 6, 8]

print("\n🎮 Testing gripper servos with BIG movements...")
print("Watch each servo move A LOT!\n")

for servo in turn_servos:
    print(f"Testing Servo {servo} - watch for BIG movement...")
    
    # Start at center
    controller.setTarget(servo, 6000)
    time.sleep(0.5)
    
    # Move FAR clockwise
    print(f"  Moving CW...")
    controller.setTarget(servo, 7500)
    time.sleep(1.0)
    
    # Move FAR counter-clockwise
    print(f"  Moving CCW...")
    controller.setTarget(servo, 4500)
    time.sleep(1.0)
    
    # Return to center
    print(f"  Returning to center...")
    controller.setTarget(servo, 6000)
    time.sleep(0.8)
    
    print(f"  ✅ Servo {servo} tested\n")
    time.sleep(0.3)

print("✅ All gripper servos tested with BIG movements!")
print("All servos returned to center (6000).\n")

controller.close()
