#!/usr/bin/env python3
"""
First-pass labeling of cube face images.
Outputs JSON with predicted colors for each sticker.
"""

import os
import json
import glob

TRAINING_DIR = "/home/luminerdy/rcubed/training_scans"
OUTPUT_FILE = "/home/luminerdy/rcubed/labels_first_pass.json"

def get_all_images():
    """Get all face images from training scans."""
    images = []
    
    # New format (folders)
    for scan_dir in sorted(glob.glob(os.path.join(TRAINING_DIR, "scan_*"))):
        if os.path.isdir(scan_dir):
            for face_file in sorted(glob.glob(os.path.join(scan_dir, "face_*.jpg"))):
                images.append(face_file)
    
    # Old format (flat files) 
    for f in sorted(glob.glob(os.path.join(TRAINING_DIR, "scan_*_face_*.jpg"))):
        images.append(f)
    
    return images

def main():
    images = get_all_images()
    print(f"Found {len(images)} images to label")
    
    # Save list for processing
    with open("/home/luminerdy/rcubed/images_to_label.txt", "w") as f:
        for img in images:
            f.write(img + "\n")
    
    print(f"Image list saved to images_to_label.txt")
    print(f"Total: {len(images)} images")

if __name__ == "__main__":
    main()
