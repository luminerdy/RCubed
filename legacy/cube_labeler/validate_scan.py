#!/usr/bin/env python3
"""
Validate a labeled scan for training data.

For training, we don't need Kociemba validation (cube orientation unknown).
We just need to verify:
1. Exactly 9 stickers of each color
2. Each center color appears exactly once
3. All faces have 3x3 grids
"""

import sys
import json
from pathlib import Path

def validate_scan(scan_id):
    """
    Load a labeled scan and validate for training data.
    Returns (valid: bool, message: str)
    """
    label_file = Path(__file__).parent / 'data' / 'labels' / f'scan_{scan_id}.json'
    
    if not label_file.exists():
        return False, f"Label file not found: {label_file}"
    
    with open(label_file, 'r') as f:
        data = json.load(f)
    
    # Check if verified
    if not data.get('verified', False):
        return False, "Scan not verified yet"
    
    faces = data['faces']
    
    # Validation 1: Check all faces have 3x3 grids
    for face_name, face_data in faces.items():
        grid = face_data['grid']
        if len(grid) != 3:
            return False, f"{face_name} face: expected 3 rows, got {len(grid)}"
        for i, row in enumerate(grid):
            if len(row) != 3:
                return False, f"{face_name} face row {i}: expected 3 stickers, got {len(row)}"
    
    # Validation 2: Count all colors
    color_counts = {}
    centers = []
    
    for face_name, face_data in faces.items():
        grid = face_data['grid']
        for i, row in enumerate(grid):
            for j, color in enumerate(row):
                # Count color
                color_counts[color] = color_counts.get(color, 0) + 1
                
                # Track centers (position [1][1])
                if i == 1 and j == 1:
                    centers.append(color)
    
    # Validation 3: Must have exactly 9 of each color (W, Y, R, O, B, G)
    expected_colors = ['W', 'Y', 'R', 'O', 'B', 'G']
    for color in expected_colors:
        count = color_counts.get(color, 0)
        if count != 9:
            return False, f"Color {color}: expected 9, got {count}"
    
    # Check for unexpected colors
    for color in color_counts:
        if color not in expected_colors:
            return False, f"Unexpected color: {color}"
    
    # Validation 4: All 6 center colors must be different
    if len(set(centers)) != 6:
        return False, f"Centers must be 6 different colors, got: {centers}"
    
    # All validations passed
    return True, f"Valid! Colors: {color_counts}, Centers: {sorted(set(centers))}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_scan.py <scan_id>")
        print("Example: python3 validate_scan.py 4")
        sys.exit(1)
    
    scan_id = int(sys.argv[1])
    
    print(f"Validating scan {scan_id}...")
    valid, message = validate_scan(scan_id)
    
    if valid:
        print(f"✅ VALID - {message}")
    else:
        print(f"❌ INVALID - {message}")
        sys.exit(1)

if __name__ == '__main__':
    main()
