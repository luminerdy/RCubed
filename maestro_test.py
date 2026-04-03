#!/usr/bin/env python3
"""
RCubed Maestro Test Script
Tests all servo channels on the Pololu Mini Maestro 12-Channel controller
"""

import sys
import time
import os

# Add current directory to path for maestro.py import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import maestro
except ImportError:
    print("❌ Error: maestro.py not found in current directory")
    print("Run: wget https://raw.githubusercontent.com/FRC4564/Maestro/master/maestro.py")
    sys.exit(1)

# Servo configuration from rcubed-servo-mapping.md
SERVO_MAP = {
    0: "Left-Bottom Rotate",
    1: "Left-Bottom Approach",
    2: "Top Rotate",
    3: "Top Approach",
    4: "(spare)",
    5: "(spare)",
    6: "Right Rotate",
    7: "Right Approach",
    8: "Bottom Rotate",
    9: "Bottom Approach",
    10: "(spare)",
    11: "(spare)"
}

# Safe test positions (quarter-microsecond units)
# 6000 = 1.5ms = center position for most servos
CENTER = 6000
MIN_SAFE = 4000   # 1.0ms
MAX_SAFE = 8000   # 2.0ms

def test_single_servo(controller, channel):
    """Test a single servo with a small movement"""
    print(f"\n🎮 Testing Channel {channel}: {SERVO_MAP.get(channel, 'Unknown')}")
    
    try:
        # Move to center
        print(f"  → Moving to center ({CENTER})...")
        controller.setTarget(channel, CENTER)
        time.sleep(0.5)
        
        # Small movement down
        print(f"  → Moving to {CENTER - 500}...")
        controller.setTarget(channel, CENTER - 500)
        time.sleep(0.5)
        
        # Small movement up
        print(f"  → Moving to {CENTER + 500}...")
        controller.setTarget(channel, CENTER + 500)
        time.sleep(0.5)
        
        # Return to center
        print(f"  → Returning to center...")
        controller.setTarget(channel, CENTER)
        time.sleep(0.3)
        
        print(f"  ✅ Channel {channel} responding")
        return True
        
    except Exception as e:
        print(f"  ❌ Error on channel {channel}: {e}")
        return False

def test_all_servos(controller):
    """Test all servo channels"""
    print("\n" + "=" * 60)
    print("RCubed Maestro - All Channel Test")
    print("=" * 60)
    
    results = {}
    active_channels = [0, 1, 2, 3, 6, 7, 8, 9]  # Skip spare channels (4, 5, 10, 11)
    
    for channel in active_channels:
        results[channel] = test_single_servo(controller, channel)
        time.sleep(0.2)  # Brief pause between servos
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    working = sum(1 for v in results.values() if v)
    total = len(results)
    
    for channel, success in sorted(results.items()):
        status = "✅" if success else "❌"
        print(f"{status} Channel {channel:2d}: {SERVO_MAP.get(channel, 'Unknown'):20s}")
    
    print(f"\nResult: {working}/{total} channels responding")
    return all(results.values())

def main():
    print("🎲 RCubed Maestro Connection Test")
    print("=" * 60)
    
    # Try both possible device paths
    device_paths = ['/dev/ttyACM0', '/dev/ttyACM1']
    controller = None
    
    for device in device_paths:
        try:
            print(f"Trying {device}...")
            controller = maestro.Controller(device)
            print(f"✅ Connected to Maestro on {device}")
            break
        except Exception as e:
            print(f"   {device} not available: {e}")
            continue
    
    if controller is None:
        print("\n❌ Could not connect to Maestro")
        print("Check:")
        print("  - USB cable connected?")
        print("  - Maestro powered on?")
        print("  - Run: ls -l /dev/ttyACM*")
        sys.exit(1)
    
    # Check if user wants to test all or specific channel
    if len(sys.argv) > 1:
        try:
            channel = int(sys.argv[1])
            if 0 <= channel <= 11:
                test_single_servo(controller, channel)
            else:
                print(f"❌ Invalid channel: {channel} (must be 0-11)")
        except ValueError:
            print("❌ Invalid channel number")
    else:
        # Test all servos
        success = test_all_servos(controller)
        
        if success:
            print("\n🎉 All servos responding! Ready for calibration.")
        else:
            print("\n⚠️  Some servos not responding. Check connections.")
    
    # Clean up
    controller.close()
    print("\n✅ Test complete!")

if __name__ == "__main__":
    main()
