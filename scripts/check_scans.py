#!/usr/bin/env python3
"""
Quick check: What face centers are in each scan image?
"""
import cv2
from pathlib import Path

scans = [
    ("face_1_front.jpg", "Front"),
    ("face_2_back.jpg", "Back"),
    ("face_3_right.jpg", "Right"),
    ("face_4_left.jpg", "Left"),
    ("face_5_top.jpg", "Top"),
    ("face_6_bottom.jpg", "Bottom"),
]

print("Scan Image Analysis")
print("=" * 60)

for filename, label in scans:
    path = Path("scans") / filename
    if path.exists():
        img = cv2.imread(str(path))
        h, w = img.shape[:2]
        # Extract center sticker (middle of 3x3 grid)
        center_y, center_x = h // 2, w // 2
        region = img[center_y-20:center_y+20, center_x-20:center_x+20]
        
        # Get average color
        avg_color = region.mean(axis=(0,1))  # BGR
        b, g, r = avg_color
        
        # Simple color detection
        if b > 200 and g > 200 and r > 200:
            color = "WHITE"
        elif b > 150 and g > 150 and r < 100:
            color = "BLUE (or YELLOW?)"
        elif r > 150 and g < 100 and b < 100:
            color = "RED"
        elif r < 100 and g > 150 and b < 100:
            color = "GREEN"
        elif r > 150 and g > 100 and b < 100:
            color = "ORANGE or YELLOW"
        else:
            color = f"Unknown (R={r:.0f} G={g:.0f} B={b:.0f})"
        
        print(f"{label:8} ({filename:20}) → {color}")
    else:
        print(f"{label:8} ({filename:20}) → FILE NOT FOUND")

print("\n" + "=" * 60)
print("Expected (if loaded White front / Blue top):")
print("  Front  → WHITE")
print("  Back   → YELLOW") 
print("  Right  → RED")
print("  Left   → ORANGE")
print("  Top    → BLUE")
print("  Bottom → GREEN")
