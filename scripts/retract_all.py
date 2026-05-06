#!/usr/bin/env python3
"""
Retract all grippers to their retracted positions
"""
import sys
import json
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / 'src'))
import maestro

# Load config
with open(REPO_ROOT / 'config' / 'servo_config.json', 'r') as f:
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
    (1, int(config['rp']['1']['retracted'])),
    (3, int(config['rp']['3']['retracted'])),
    (7, int(config['rp']['7']['retracted'])),
    (9, int(config['rp']['9']['retracted']))
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
