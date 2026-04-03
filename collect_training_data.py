#!/usr/bin/env python3
"""
Automated training data collection for RCubed.

Workflow:
1. Scan cube (6 faces, cropped images)
2. Auto-detect colors with OpenCV
3. Save as training data
4. Execute 3-6 random moves to scramble
5. Repeat

User manually verifies/corrects colors in web labeler afterward.
"""

import sys
import os
import time
import random
import subprocess
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Directories
SCANS_DIR = Path(__file__).parent / "scans"
TRAINING_DIR = Path(__file__).parent / "training_scans"

# Create training directory
TRAINING_DIR.mkdir(exist_ok=True)

# Available moves for scrambling
MOVES = ['R', "R'", 'R2', 'L', "L'", 'L2', 
         'U', "U'", 'U2', 'D', "D'", 'D2',
         'F', "F'", 'F2', 'B', "B'", 'B2']

def run_scan(skip_setup=False):
    """Run scan_6faces.py to capture all 6 faces."""
    print("\n🔄 Running scan...")
    cmd = ['python3', 'scan_6faces.py']
    if skip_setup:
        cmd.append('--skip-setup')
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent,
        capture_output=False
    )
    return result.returncode == 0

def move_images_to_training(scan_number):
    """
    Move scanned images to training directory with scan number prefix.
    Returns list of moved files.
    """
    moved_files = []
    
    for i in range(1, 7):
        face_names = ['front', 'back', 'right', 'left', 'top', 'bottom']
        src = SCANS_DIR / f"face_{i}_{face_names[i-1]}.jpg"
        
        if src.exists():
            dst = TRAINING_DIR / f"scan_{scan_number:03d}_face_{i}_{face_names[i-1]}.jpg"
            src.rename(dst)
            moved_files.append(dst)
            print(f"  📦 Saved: {dst.name}")
    
    return moved_files

def generate_scramble_moves(count=None):
    """
    Generate 3-6 random moves for scrambling.
    Avoids consecutive same-face moves.
    """
    if count is None:
        count = random.randint(3, 6)
    
    scramble = []
    last_face = None
    
    for _ in range(count):
        # Filter out moves on same face as previous
        if last_face:
            available = [m for m in MOVES if m[0] != last_face]
        else:
            available = MOVES
        
        move = random.choice(available)
        scramble.append(move)
        last_face = move[0]
    
    return scramble

def execute_scramble(moves):
    """
    Execute scramble moves using move_executor_v2.py.
    """
    moves_str = ' '.join(moves)
    print(f"\n🔀 Scrambling: {moves_str}")
    
    result = subprocess.run(
        ['python3', 'move_executor_v2.py', moves_str],
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("  ✓ Scramble complete")
        return True
    else:
        print(f"  ✗ Scramble failed: {result.stderr}")
        return False

def main():
    """Run training data collection loop."""
    print("🎲 RCubed Training Data Collection")
    print("=" * 60)
    print("This script will:")
    print("  1. Scan the cube (6 faces)")
    print("  2. Save cropped images to training_scans/")
    print("  3. Execute 3-6 random moves")
    print("  4. Repeat")
    print()
    print("You can verify/correct colors later in the web labeler.")
    print("=" * 60)
    print()
    
    # Get number of scans to collect
    try:
        total_scans = int(input("How many scans to collect? (recommend 50-100): "))
    except (ValueError, KeyboardInterrupt):
        print("\nCancelled.")
        return
    
    if total_scans <= 0:
        print("Must be > 0")
        return
    
    print()
    input("⏳ Load a scrambled cube, then press Enter to start...")
    print()
    
    scan_count = 0
    
    try:
        for i in range(total_scans):
            scan_number = i + 1
            print(f"\n{'='*60}")
            print(f"📸 SCAN {scan_number}/{total_scans}")
            print(f"{'='*60}")
            
            # Step 1: Scan cube
            # Skip setup for scans 2+ (cube already loaded from previous iteration)
            skip_setup = (i > 0)
            if not run_scan(skip_setup=skip_setup):
                print("❌ Scan failed!")
                break
            
            # Step 2: Move images to training directory
            moved_files = move_images_to_training(scan_number)
            if len(moved_files) != 6:
                print(f"⚠️  Only got {len(moved_files)} faces, expected 6")
            
            scan_count += 1
            
            # Step 3: Scramble for next iteration (unless last scan)
            if scan_number < total_scans:
                moves = generate_scramble_moves()
                if not execute_scramble(moves):
                    print("❌ Scramble failed!")
                    break
                
                # Short pause between scans
                time.sleep(1)
            else:
                print(f"\n🎉 Collection complete! {scan_count} scans saved.")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"  Scans collected: {scan_count}")
    print(f"  Images saved: {scan_count * 6}")
    print(f"  Location: {TRAINING_DIR}")
    print()
    print("Next steps:")
    print("  1. Open http://localhost:5000 in browser")
    print("  2. Verify/correct colors for each scan")
    print("  3. Run: cd cube_labeler && python3 export_dataset.py")
    print("  4. Train YOLOv8 model on exported data")
    print()

if __name__ == '__main__':
    main()
