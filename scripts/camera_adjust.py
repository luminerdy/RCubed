#!/usr/bin/env python3
"""
RCubed Camera Adjustment Tool
Helps find optimal exposure and brightness settings for cube color detection
"""

import cv2
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

def capture_with_settings(exposure=None, brightness=None, contrast=None):
    """Capture image with specific camera settings"""
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Failed to open camera")
        return None
    
    # Set auto-exposure off (manual mode)
    if exposure is not None:
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # Manual mode
        cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
        print(f"  Exposure: {exposure}")
    
    if brightness is not None:
        cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness)
        print(f"  Brightness: {brightness}")
    
    if contrast is not None:
        cap.set(cv2.CAP_PROP_CONTRAST, contrast)
        print(f"  Contrast: {contrast}")
    
    # Let camera adjust
    for i in range(10):
        cap.read()
    
    # Capture image
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        return frame
    return None

def test_exposure_range():
    """Test different exposure levels"""
    print("=" * 60)
    print("Camera Exposure Test")
    print("=" * 60)
    print("\nTesting different exposure levels...")
    print("Lower exposure = darker image")
    print("Higher exposure = brighter image\n")
    
    # Test range of exposures
    exposures = [-13, -11, -9, -7, -5, -3]  # Negative values = less exposure
    
    for i, exp in enumerate(exposures):
        print(f"\n📸 Test {i+1}/{len(exposures)}: Exposure = {exp}")
        frame = capture_with_settings(exposure=exp)
        
        if frame is not None:
            filename = str(REPO_ROOT / f"exposure_test_{exp}.jpg")
            cv2.imwrite(filename, frame)
            
            # Calculate average brightness
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            avg_brightness = gray.mean()
            
            print(f"  ✅ Saved: {filename}")
            print(f"  Average brightness: {avg_brightness:.1f} / 255")
            
            if avg_brightness < 80:
                print("  → Too dark")
            elif avg_brightness > 180:
                print("  → Too bright")
            else:
                print("  → Good range ✓")
    
    print("\n" + "=" * 60)
    print("Review the test images:")
    print("  ls -lh ~/rcubed/exposure_test_*.jpg")
    print("\nPick the exposure that shows cube colors most clearly.")
    print("Ideal: Colors look vibrant, not washed out or too dark")

def interactive_adjust():
    """Interactive camera adjustment"""
    print("=" * 60)
    print("Interactive Camera Adjustment")
    print("=" * 60)
    
    print("\nCurrent auto settings:")
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        exposure = cap.get(cv2.CAP_PROP_EXPOSURE)
        brightness = cap.get(cv2.CAP_PROP_BRIGHTNESS)
        contrast = cap.get(cv2.CAP_PROP_CONTRAST)
        
        print(f"  Exposure: {exposure}")
        print(f"  Brightness: {brightness}")
        print(f"  Contrast: {contrast}")
        cap.release()
    
    print("\nLet's find the best exposure...")
    
    # Start with moderate exposure
    current_exposure = -7
    
    while True:
        print(f"\n📸 Testing exposure: {current_exposure}")
        frame = capture_with_settings(exposure=current_exposure)
        
        if frame is None:
            print("❌ Failed to capture")
            return
        
        # Save preview
        cv2.imwrite(str(REPO_ROOT / 'preview.jpg'), frame)
        
        # Calculate brightness
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        avg_brightness = gray.mean()
        
        print(f"  Average brightness: {avg_brightness:.1f} / 255")
        print(f"  Preview saved: ~/rcubed/preview.jpg")
        
        print("\nOptions:")
        print("  + : Brighter (higher exposure)")
        print("  - : Darker (lower exposure)")
        print("  s : Save this setting")
        print("  q : Quit")
        
        choice = input("\nChoice: ").strip().lower()
        
        if choice == '+':
            current_exposure += 1
        elif choice == '-':
            current_exposure -= 1
        elif choice == 's':
            print(f"\n✅ Recommended exposure: {current_exposure}")
            print(f"\nTo use this in your scripts:")
            print(f"  cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)")
            print(f"  cap.set(cv2.CAP_PROP_EXPOSURE, {current_exposure})")
            return current_exposure
        elif choice == 'q':
            return None

def main():
    print("\n🎥 RCubed Camera Adjustment Tool\n")
    
    print("Choose mode:")
    print("  1. Test exposure range (auto)")
    print("  2. Interactive adjustment")
    
    choice = input("\nMode (1/2): ").strip()
    
    if choice == '1':
        test_exposure_range()
    elif choice == '2':
        interactive_adjust()
    else:
        print("Invalid choice")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
