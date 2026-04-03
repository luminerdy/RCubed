#!/usr/bin/env python3
"""
RCubed Camera Test Script
Captures a test image from the webcam to verify setup
"""

import cv2
import sys
import os

def test_camera(device_id=0):
    """Test camera capture and save an image"""
    print(f"🎥 Testing camera on /dev/video{device_id}...")
    
    # Open camera
    cap = cv2.VideoCapture(device_id)
    
    if not cap.isOpened():
        print(f"❌ Failed to open camera /dev/video{device_id}")
        return False
    
    # Get camera properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    print(f"✅ Camera opened successfully")
    print(f"   Resolution: {width}x{height}")
    print(f"   FPS: {fps}")
    
    # Capture a few frames to let camera adjust
    print("📸 Warming up camera...")
    for i in range(5):
        ret, frame = cap.read()
        if not ret:
            print(f"❌ Failed to capture frame {i+1}")
            cap.release()
            return False
    
    # Capture final test image
    print("📸 Capturing test image...")
    ret, frame = cap.read()
    
    if not ret:
        print("❌ Failed to capture test image")
        cap.release()
        return False
    
    # Save test image
    output_path = os.path.expanduser("~/rcubed/camera_test.jpg")
    cv2.imwrite(output_path, frame)
    print(f"✅ Test image saved to: {output_path}")
    print(f"   Image shape: {frame.shape}")
    
    # Release camera
    cap.release()
    
    return True

def main():
    print("=" * 60)
    print("RCubed Camera Test")
    print("=" * 60)
    
    # Try video0 first (most likely the USB webcam)
    if test_camera(0):
        print("\n🎉 Camera test successful!")
        print("\nNext steps:")
        print("  1. View test image: ~/rcubed/camera_test.jpg")
        print("  2. Check if cube is visible and in focus")
        print("  3. Adjust camera position/angle if needed")
        print("  4. Run color calibration to detect cube faces")
        return 0
    else:
        print("\n⚠️  Camera 0 failed, trying camera 1...")
        if test_camera(1):
            print("\n🎉 Camera test successful (using video1)!")
            print("Note: Update scripts to use device_id=1")
            return 0
        else:
            print("\n❌ Camera test failed")
            print("Check:")
            print("  - Is camera connected?")
            print("  - Is camera recognized? (lsusb | grep -i camera)")
            print("  - Permissions? (add user to video group)")
            return 1

if __name__ == "__main__":
    sys.exit(main())
