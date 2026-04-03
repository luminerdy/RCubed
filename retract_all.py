#!/usr/bin/env python3
"""
Retract all grippers to their retracted positions
"""
import sys
import json
import time

sys.path.insert(0, '/home/luminerdy/rcubed')
import maestro

# Load config
with open('/home/luminerdy/rcubed/servo_config.json', 'r') as f:
    config = json.load(f)

# Connect to Maestro
try:
    controller = maestro.Controller('/dev/ttyACM0')
    print("✅ Connected to Maestro")
except:
    controller = maestro.Controller('/dev/ttyACM1')
    print("✅ Connected to Maestro on ACM1")

print("\n⬅️  Retracting all grippers...")

# MOVE servos: 1, 3, 7, 9
servos_and_positions = [
    (1, int(config['1']['positions']['retracted'])),
    (3, int(config['3']['positions']['retracted'])),
    (7, int(config['7']['positions']['retracted'])),
    (9, int(config['9']['positions']['retracted']))
]

for servo, pos in servos_and_positions:
    print(f"  Servo {servo} → {pos}")
    controller.setTarget(servo, pos)
    time.sleep(0.3)

print("\n✅ All grippers should be retracted!")
print("\nPositions sent:")
for servo, pos in servos_and_positions:
    print(f"  Servo {servo}: {pos}")

controller.close()
