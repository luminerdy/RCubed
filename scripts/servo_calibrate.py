#!/usr/bin/env python3
"""
RCubed Servo Calibration Tool
Interactive script to find safe min/max positions and functional positions for each servo
"""

import sys
import os
import json
import time

from pathlib import Path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / 'src'))

try:
    import maestro
except ImportError:
    print("❌ Error: maestro.py not found")
    sys.exit(1)

# Servo configuration
SERVOS = {
    0: {"name": "Left-Bottom TURN", "type": "turn"},
    1: {"name": "Left-Bottom MOVE", "type": "move"},
    2: {"name": "Top TURN", "type": "turn"},
    3: {"name": "Top MOVE", "type": "move"},
    6: {"name": "Right TURN", "type": "turn"},
    7: {"name": "Right MOVE", "type": "move"},
    8: {"name": "Bottom TURN", "type": "turn"},
    9: {"name": "Bottom MOVE", "type": "move"}
}

CONFIG_FILE = Path(__file__).parent.parent / 'config' / 'servo_config.json'

class ServoCalibrator:
    def __init__(self):
        self.controller = None
        self.config = {}
        
    def connect(self):
        """Connect to Maestro controller"""
        try:
            self.controller = maestro.Controller('/dev/ttyACM0')
            print("✅ Connected to Maestro on /dev/ttyACM0")
            return True
        except Exception as e:
            try:
                self.controller = maestro.Controller('/dev/ttyACM1')
                print("✅ Connected to Maestro on /dev/ttyACM1")
                return True
            except Exception as e2:
                print(f"❌ Failed to connect: {e}")
                return False
    
    def calibrate_servo(self, channel):
        """Interactively calibrate a single servo"""
        servo_info = SERVOS[channel]
        print("\n" + "=" * 60)
        print(f"Calibrating Servo {channel}: {servo_info['name']}")
        print("=" * 60)
        
        # Start at center position
        current_pos = 6000
        self.controller.setTarget(channel, current_pos)
        print(f"\nStarting at center position: {current_pos}")
        print(f"Current position will be shown as you adjust.")
        
        # Interactive adjustment
        print("\nControls:")
        print("  +/- : Adjust by 100 units")
        print("  >/< : Adjust by 500 units")
        print("  n   : Save current position as a named position")
        print("  q   : Finish this servo")
        print()
        
        positions = {}
        
        while True:
            print(f"\rCurrent: {current_pos:4d}  ", end='', flush=True)
            
            cmd = input("\nCommand (+/-/>/</n/q): ").strip().lower()
            
            if cmd == 'q':
                break
            elif cmd == '+':
                current_pos = min(current_pos + 100, 8000)
                self.controller.setTarget(channel, current_pos)
            elif cmd == '-':
                current_pos = max(current_pos - 100, 4000)
                self.controller.setTarget(channel, current_pos)
            elif cmd == '>':
                current_pos = min(current_pos + 500, 8000)
                self.controller.setTarget(channel, current_pos)
            elif cmd == '<':
                current_pos = max(current_pos - 500, 4000)
                self.controller.setTarget(channel, current_pos)
            elif cmd == 'n':
                name = input("Position name: ").strip()
                positions[name] = current_pos
                print(f"✅ Saved '{name}' = {current_pos}")
            else:
                print("Invalid command")
        
        # Return to center
        self.controller.setTarget(channel, 6000)
        time.sleep(0.3)
        
        return positions
    
    def calibrate_all(self):
        """Calibrate all servos"""
        print("\n" + "=" * 60)
        print("RCubed Servo Calibration")
        print("=" * 60)
        print("\nThis tool will help you find the safe operating range")
        print("for each servo and save key positions.")
        print("\n⚠️  IMPORTANT:")
        print("  - Start with small adjustments")
        print("  - Watch the servo - STOP if it binds or strains")
        print("  - Don't force servos past their mechanical limits")
        print()
        
        # Load existing config if available
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
                print(f"✅ Loaded existing config from {CONFIG_FILE}")
            except Exception as e:
                print(f"⚠️  Could not load config: {e}")
                self.config = {}
        
        for channel in sorted(SERVOS.keys()):
            servo_info = SERVOS[channel]
            
            print(f"\n{'=' * 60}")
            print(f"Next: Servo {channel} - {servo_info['name']} ({servo_info['type']})")
            
            if servo_info['type'] == 'turn':
                print("\n⭐ For TURN servos (BIDIRECTIONAL ±90°), find:")
                print("  - neutral: Starting position (0°)")
                print("  - turn_cw_90: Clockwise 90° rotation (U, R, F moves)")
                print("  - turn_ccw_90: Counter-clockwise 90° (U', R', F' moves)")
                print("  → Both directions REQUIRED for fast solving!")
            elif servo_info['type'] == 'move':
                print("\nFor MOVE servos, find:")
                print("  - retracted: Gripper away from cube (released)")
                print("  - engaged: Gripper touching cube (gripping)")
            
            response = input("\nCalibrate this servo? (y/n/skip all): ").strip().lower()
            
            if response == 'skip all':
                break
            elif response == 'y':
                positions = self.calibrate_servo(channel)
                
                # Save to config
                self.config[str(channel)] = {
                    "name": servo_info['name'],
                    "type": servo_info['type'],
                    "positions": positions
                }
                
                print(f"\n✅ Saved positions for servo {channel}:")
                for name, pos in positions.items():
                    print(f"   {name}: {pos}")
            else:
                print("⏭️  Skipped")
        
        # Save config
        self.save_config()
    
    def save_config(self):
        """Save calibration config to file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"\n✅ Configuration saved to {CONFIG_FILE}")
            print("\nYou can now use these positions in your control scripts!")
        except Exception as e:
            print(f"\n❌ Failed to save config: {e}")
    
    def close(self):
        """Clean up"""
        if self.controller:
            # Return all servos to center
            print("\n🔄 Returning all servos to center position...")
            for channel in SERVOS.keys():
                self.controller.setTarget(channel, 6000)
            time.sleep(0.5)
            self.controller.close()
            print("✅ Controller closed")

def main():
    calibrator = ServoCalibrator()
    
    if not calibrator.connect():
        return 1
    
    try:
        calibrator.calibrate_all()
    except KeyboardInterrupt:
        print("\n\n⚠️  Calibration interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        calibrator.close()
    
    print("\n" + "=" * 60)
    print("Calibration Complete!")
    print("=" * 60)
    print(f"Config file: {CONFIG_FILE}")
    print("\nNext steps:")
    print("  1. Review saved positions")
    print("  2. Test cube manipulation sequences")
    print("  3. Fine-tune positions if needed")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
