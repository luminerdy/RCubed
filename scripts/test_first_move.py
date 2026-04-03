#!/usr/bin/env python3
"""
Test first move: Top face 90° rotation
Starting state: All grippers engaged, TURN servos at position A
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

print("\n🎲 Testing U move (top face clockwise 90°)")
print("=" * 60)

# Starting state: all engaged, TURN at position A
# We'll rotate the TOP face (servo 2 TURN, servo 3 MOVE)

turn_servo = 2
move_servo = 3

# Get positions
pos_a = int(config['2']['positions']['pos_a'])
pos_b = int(config['2']['positions']['pos_b'])
move_retracted = int(config['3']['positions']['retracted'])
move_engaged = int(config['3']['positions']['engaged'])

print(f"\nUsing:")
print(f"  Turn servo {turn_servo}: A={pos_a}, B={pos_b}")
print(f"  Move servo {move_servo}: retracted={move_retracted}, engaged={move_engaged}")

print("\nSequence:")
print("  1. All other grippers stay engaged (to hold cube)")
print("  2. Top gripper already engaged - ready!")
print("  3. Rotate top face: A → B (90° turn)")
print("  4. Retract top gripper")
print("  5. Retract all grippers to finish\n")

input("Press ENTER to start the move...")

# Step 1: Top gripper is already engaged - perfect!
print("\n1. ✓ Top gripper already engaged")
time.sleep(0.5)

# Step 2: Rotate the top face from A to B
print("2. 🔄 Rotating top face A → B (90°)...")
controller.setTarget(turn_servo, pos_b)
time.sleep(1.5)
print("   ✓ Rotation complete!")

# Step 3: Retract top gripper
print("3. ⬅️  Retracting top gripper...")
controller.setTarget(move_servo, move_retracted)
time.sleep(1.0)
print("   ✓ Top gripper retracted")

# Step 4: Retract all grippers to finish
print("4. ⬅️  Retracting all grippers...")
controller.setTarget(1, int(config['1']['positions']['retracted']))
controller.setTarget(7, int(config['7']['positions']['retracted']))
controller.setTarget(9, int(config['9']['positions']['retracted']))
time.sleep(1.0)
print("   ✓ All grippers retracted")

print("\n✅ U move complete!")
print(f"   Turn servo {turn_servo} now at position B")
print(f"   All grippers retracted")
print(f"\nNext U move will go B → A\n")

controller.close()
