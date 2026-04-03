#!/usr/bin/env python3
"""
RCubed Color Detection Test
Simple script to detect and display Rubik's cube colors from camera feed
"""

import cv2
import numpy as np
import sys

# HSV color ranges for Rubik's cube stickers
# These are starting values - will need calibration
COLOR_RANGES = {
    'red': {
        'lower1': np.array([0, 100, 100]),
        'upper1': np.array([10, 255, 255]),
        'lower2': np.array([170, 100, 100]),  # Red wraps around in HSV
        'upper2': np.array([180, 255, 255])
    },
    'orange': {
        'lower': np.array([10, 100, 100]),
        'upper': np.array([25, 255, 255])
    },
    'yellow': {
        'lower': np.array([25, 100, 100]),
        'upper': np.array([35, 255, 255])
    },
    'green': {
        'lower': np.array([40, 50, 50]),
        'upper': np.array([80, 255, 255])
    },
    'blue': {
        'lower': np.array([90, 50, 50]),
        'upper': np.array([130, 255, 255])
    },
    'white': {
        'lower': np.array([0, 0, 200]),
        'upper': np.array([180, 30, 255])
    }
}

def detect_colors(frame):
    """Detect cube colors in frame"""
    # Convert to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    detected = {}
    
    for color_name, ranges in COLOR_RANGES.items():
        if 'lower1' in ranges:
            # Red needs two ranges (wraps around HSV hue circle)
            mask1 = cv2.inRange(hsv, ranges['lower1'], ranges['upper1'])
            mask2 = cv2.inRange(hsv, ranges['lower2'], ranges['upper2'])
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            mask = cv2.inRange(hsv, ranges['lower'], ranges['upper'])
        
        # Count pixels
        pixel_count = cv2.countNonZero(mask)
        detected[color_name] = pixel_count
    
    return detected

def main():
    print("=" * 60)
    print("RCubed Color Detection Test")
    print("=" * 60)
    print("\nThis script captures an image and detects cube colors.")
    print("Place the cube in front of the camera with good lighting.")
    print("\nPress ENTER when ready...")
    input()
    
    # Open camera
    print("\n📸 Opening camera...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Failed to open camera")
        return 1
    
    print("✅ Camera opened")
    
    # Let camera adjust
    print("📸 Warming up...")
    for i in range(10):
        cap.read()
    
    # Capture image
    print("📸 Capturing image...")
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("❌ Failed to capture image")
        return 1
    
    # Save original
    cv2.imwrite('/home/luminerdy/rcubed/color_test_original.jpg', frame)
    print(f"✅ Original saved: ~/rcubed/color_test_original.jpg")
    
    # Detect colors
    print("\n🎨 Detecting colors...")
    detected = detect_colors(frame)
    
    # Sort by pixel count
    sorted_colors = sorted(detected.items(), key=lambda x: x[1], reverse=True)
    
    print("\nColor Detection Results:")
    print("-" * 40)
    for color, pixels in sorted_colors:
        if pixels > 100:  # Only show colors with significant presence
            percentage = (pixels / (frame.shape[0] * frame.shape[1])) * 100
            bar = "█" * int(percentage / 2)
            print(f"{color:8s}: {pixels:6d} px ({percentage:5.2f}%) {bar}")
    
    # Create visualization with color masks
    print("\n📊 Creating visualization...")
    
    # Create a grid to show each color mask
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    masks = []
    
    for color_name in ['red', 'orange', 'yellow', 'green', 'blue', 'white']:
        ranges = COLOR_RANGES[color_name]
        if 'lower1' in ranges:
            mask1 = cv2.inRange(hsv, ranges['lower1'], ranges['upper1'])
            mask2 = cv2.inRange(hsv, ranges['lower2'], ranges['upper2'])
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            mask = cv2.inRange(hsv, ranges['lower'], ranges['upper'])
        
        # Convert mask to BGR for display
        mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        
        # Add label
        cv2.putText(mask_bgr, color_name.upper(), (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        masks.append(mask_bgr)
    
    # Combine masks into grid (2 rows x 3 cols)
    row1 = np.hstack(masks[0:3])
    row2 = np.hstack(masks[3:6])
    grid = np.vstack([row1, row2])
    
    # Save visualization
    cv2.imwrite('/home/luminerdy/rcubed/color_test_masks.jpg', grid)
    print(f"✅ Masks saved: ~/rcubed/color_test_masks.jpg")
    
    print("\n" + "=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print("1. Review the mask images to see which colors are detected")
    print("2. If colors are not detected well, adjust lighting")
    print("3. May need to fine-tune HSV ranges for your specific cube")
    print("4. Once colors look good, proceed to cube face scanning")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
