#!/usr/bin/env python3
"""
Test a single face rotation using calibrated two-position values
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

print("\n🎲 Testing a single face rotation (U move - top face)")
print("Using two-position toggle method\n")

# Top face = servo 2 (TURN) + servo 3 (MOVE)
turn_servo = 2
move_servo = 3

# Get positions from config
pos_a = int(config['2']['positions']['pos_a'])
pos_b = int(config['2']['positions']['pos_b'])
retracted = int(config['3']['positions']['retracted'])
engaged = int(config['3']['positions']['engaged'])

print(f"Turn servo {turn_servo}: pos_a={pos_a}, pos_b={pos_b}")
print(f"Move servo {move_servo}: retracted={retracted}, engaged={engaged}\n")

# Assume gripper is currently at position A
current_turn_pos = 'a'

print("Executing U move (top face clockwise 90°):")
print("1. Approach - move gripper forward")
controller.setTarget(move_servo, engaged)
time.sleep(0.8)

print("2. Turn - rotate from A to B (90°)")
if current_turn_pos == 'a':
    controller.setTarget(turn_servo, pos_b)
    current_turn_pos = 'b'
else:
    controller.setTarget(turn_servo, pos_a)
    current_turn_pos = 'a'
time.sleep(1.2)

print("3. Retract - move gripper back")
controller.setTarget(move_servo, retracted)
time.sleep(0.8)

print(f"\n✅ U move complete! Turn servo now at position {current_turn_pos}")
print(f"Next move will go from {current_turn_pos} → {'a' if current_turn_pos == 'b' else 'b'}\n")

controller.close()
