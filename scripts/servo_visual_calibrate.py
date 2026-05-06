#!/usr/bin/env python3
"""
RCubed Visual Servo Calibration
Interactive calibration with camera feedback sent to Telegram
"""

import sys
import os
import json
import time
import cv2
import requests

from pathlib import Path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / 'src'))

try:
    import maestro
except ImportError:
    print("❌ Error: maestro.py not found")
    sys.exit(1)

# Telegram configuration
TELEGRAM_BOT_TOKEN = "7700523599:AAEUfZbt9lJP0XffP6oZaMgfLUXfqjEyveM"
TELEGRAM_CHAT_ID = "8594925025"

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

CONFIG_FILE = REPO_ROOT / 'config' / 'servo_config.json'

def send_telegram_photo(image_path, caption):
    """Send photo to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        with open(image_path, 'rb') as photo:
            files = {'photo': photo}
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'caption': caption,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, files=files, data=data, timeout=10)
            return response.json().get('ok', False)
    except Exception as e:
        print(f"⚠️  Telegram send failed: {e}")
        return False

def capture_image(filename=None):
    if filename is None:
        filename = str(Path(__file__).parent.parent / 'calibration_view.jpg')
    """Capture image from camera"""
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Camera failed to open")
        return None
    
    # Warm up camera
    for i in range(5):
        cap.read()
    
    # Capture
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        cv2.imwrite(filename, frame)
        return filename
    return None

class VisualCalibrator:
    def __init__(self):
        self.controller = None
        self.config = {}
        
    def connect(self):
        """Connect to Maestro"""
        try:
            self.controller = maestro.Controller('/dev/ttyACM0')
            print("✅ Connected to Maestro on /dev/ttyACM0")
            return True
        except Exception as e:
            try:
                self.controller = maestro.Controller('/dev/ttyACM1')
                print("✅ Connected to Maestro on /dev/ttyACM1")
                return True
            except:
                print(f"❌ Failed to connect: {e}")
                return False
    
    def move_and_show(self, channel, position, description=""):
        """Move servo and capture photo"""
        # Move servo
        self.controller.setTarget(channel, position)
        time.sleep(0.5)  # Wait for movement
        
        # Capture image
        img_path = capture_image()
        if img_path:
            # Send to Telegram
            caption = f"<b>Servo {channel}: {SERVOS[channel]['name']}</b>\n"
            caption += f"Position: {position}\n"
            if description:
                caption += f"{description}"
            
            send_telegram_photo(img_path, caption)
            print(f"📸 Photo sent - Servo {channel} at {position}")
        else:
            print("⚠️  Photo capture failed")
    
    def calibrate_servo(self, channel):
        """Visual calibration for one servo"""
        servo_info = SERVOS[channel]
        
        print("\n" + "=" * 60)
        print(f"Calibrating Servo {channel}: {servo_info['name']}")
        print("=" * 60)
        
        # Start at center
        current_pos = 6000
        self.move_and_show(channel, current_pos, "Starting at center (6000)")
        
        positions = {}
        
        print("\nCommands:")
        print("  + : Increase by 100")
        print("  - : Decrease by 100")
        print("  > : Increase by 500")
        print("  < : Decrease by 500")
        print("  s <name> : Save current position")
        print("  d : Done with this servo")
        print()
        
        if servo_info['type'] == 'turn':
            print("Suggested positions to save:")
            print("  - neutral (starting position)")
            print("  - turn_cw_90 (90° clockwise)")
            print("  - turn_ccw_90 (90° counter-clockwise, if supported)")
        else:  # move
            print("Suggested positions to save:")
            print("  - retracted (gripper away from cube)")
            print("  - engaged (gripper gripping cube)")
        
        while True:
            cmd = input(f"\n[Servo {channel} @ {current_pos}] Command: ").strip()
            
            if cmd == 'd':
                break
            elif cmd == '+':
                current_pos = min(current_pos + 100, 8000)
                self.move_and_show(channel, current_pos, "Increased +100")
            elif cmd == '-':
                current_pos = max(current_pos - 100, 4000)
                self.move_and_show(channel, current_pos, "Decreased -100")
            elif cmd == '>':
                current_pos = min(current_pos + 500, 8000)
                self.move_and_show(channel, current_pos, "Increased +500")
            elif cmd == '<':
                current_pos = max(current_pos - 500, 4000)
                self.move_and_show(channel, current_pos, "Decreased -500")
            elif cmd.startswith('s '):
                name = cmd[2:].strip()
                positions[name] = current_pos
                print(f"✅ Saved '{name}' = {current_pos}")
                
                # Send confirmation photo
                caption = f"<b>✅ SAVED</b>\n"
                caption += f"Servo {channel}: {SERVOS[channel]['name']}\n"
                caption += f"<b>{name}</b> = {current_pos}"
                img_path = capture_image()
                if img_path:
                    send_telegram_photo(img_path, caption)
            else:
                print("Invalid command")
        
        # Return to center
        self.controller.setTarget(channel, 6000)
        time.sleep(0.3)
        
        return positions
    
    def calibrate_all(self):
        """Calibrate all servos with visual feedback"""
        print("\n" + "=" * 60)
        print("🎥 RCubed Visual Servo Calibration")
        print("=" * 60)
        print("\nPhotos will be sent to Telegram after each servo movement")
        print("so we can both see what's happening!\n")
        
        # Send start notification
        send_telegram_photo(
            capture_image(),
            "🚀 <b>Starting RCubed Calibration!</b>\n\nReady to calibrate servos with visual feedback."
        )
        
        # Load existing config if available
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
                print(f"✅ Loaded existing config")
            except:
                self.config = {}
        
        for channel in sorted(SERVOS.keys()):
            servo_info = SERVOS[channel]
            
            print(f"\n{'=' * 60}")
            print(f"Next: Servo {channel} - {servo_info['name']}")
            
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
        
        # Send completion notification
        send_telegram_photo(
            capture_image(),
            f"✅ <b>Calibration Complete!</b>\n\nConfig saved to:\n{CONFIG_FILE}"
        )
    
    def save_config(self):
        """Save configuration"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"\n✅ Configuration saved to {CONFIG_FILE}")
        except Exception as e:
            print(f"\n❌ Failed to save: {e}")
    
    def close(self):
        """Clean up"""
        if self.controller:
            print("\n🔄 Returning servos to center...")
            for channel in SERVOS.keys():
                self.controller.setTarget(channel, 6000)
            time.sleep(0.5)
            self.controller.close()
            print("✅ Done")

def main():
    calibrator = VisualCalibrator()
    
    if not calibrator.connect():
        return 1
    
    try:
        calibrator.calibrate_all()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        calibrator.close()
    
    print("\n" + "=" * 60)
    print("🎉 Calibration Session Complete!")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
