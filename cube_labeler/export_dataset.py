#!/usr/bin/env python3
"""
Export labeled cube data to YOLO format for training.
Creates train/val split and proper directory structure.
"""

import json
import shutil
from pathlib import Path
import random

# Paths
LABELS_DIR = Path('data/labels')
IMAGES_DIR = Path('data/images')
OUTPUT_DIR = Path('../training_data')

# YOLO class mapping
CLASS_NAMES = ['W', 'Y', 'R', 'O', 'B', 'G']
CLASS_TO_ID = {name: i for i, name in enumerate(CLASS_NAMES)}

# Grid positions for bounding boxes (normalized 0-1)
# Images are now pre-cropped to just the face region (280x325 pixels)
# No need to account for original image offset - face fills the whole image

def get_sticker_bbox(row, col, img_width=280, img_height=325):
    """
    Calculate normalized YOLO bounding box for a sticker.
    NOTE: Images are pre-cropped, so face fills entire image (280x325).
    
    Returns:
        tuple: (x_center, y_center, width, height) all normalized 0-1
    """
    # Sticker dimensions (face divided into 3×3 grid)
    sticker_w = img_width / 3
    sticker_h = img_height / 3
    
    # Sticker position in image coordinates
    x = (col * sticker_w) + (sticker_w / 2)
    y = (row * sticker_h) + (sticker_h / 2)
    
    # Normalize to 0-1
    x_center = x / img_width
    y_center = y / img_height
    width = sticker_w / img_width
    height = sticker_h / img_height
    
    return (x_center, y_center, width, height)

def export_yolo_labels(scan_labels, output_path):
    """
    Convert scan labels to YOLO format files.
    
    YOLO format: <class_id> <x_center> <y_center> <width> <height>
    One line per object, all values normalized 0-1.
    """
    # Process each face
    for face_name, face_data in scan_labels['faces'].items():
        image_file = face_data['image']
        grid = face_data['grid']
        
        # Create label file
        label_file = output_path / image_file.replace('.jpg', '.txt')
        
        with open(label_file, 'w') as f:
            for row in range(3):
                for col in range(3):
                    color = grid[row][col]
                    class_id = CLASS_TO_ID[color]
                    
                    # Get bounding box
                    x_c, y_c, w, h = get_sticker_bbox(row, col)
                    
                    # Write YOLO line
                    f.write(f"{class_id} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}\n")

def main():
    """Export all labeled scans to YOLO format."""
    print("🎲 RCubed Dataset Export")
    print("=" * 50)
    
    # Get all label files
    label_files = sorted(LABELS_DIR.glob('scan_*.json'))
    
    if not label_files:
        print("❌ No labeled scans found!")
        return
    
    print(f"📦 Found {len(label_files)} labeled scans")
    
    # Create output directories
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / 'images' / 'train').mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / 'images' / 'val').mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / 'labels' / 'train').mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / 'labels' / 'val').mkdir(parents=True, exist_ok=True)
    
    # Split train/val (80/20)
    random.shuffle(label_files)
    split_idx = int(len(label_files) * 0.8)
    train_files = label_files[:split_idx]
    val_files = label_files[split_idx:]
    
    print(f"✂️  Split: {len(train_files)} train, {len(val_files)} val")
    
    # Process train set
    print("\n📝 Processing training set...")
    for label_file in train_files:
        with open(label_file, 'r') as f:
            scan_labels = json.load(f)
        
        # Export labels
        export_yolo_labels(scan_labels, OUTPUT_DIR / 'labels' / 'train')
        
        # Copy images
        for face_data in scan_labels['faces'].values():
            src = IMAGES_DIR / face_data['image']
            dst = OUTPUT_DIR / 'images' / 'train' / face_data['image']
            shutil.copy(src, dst)
    
    # Process val set
    print("📝 Processing validation set...")
    for label_file in val_files:
        with open(label_file, 'r') as f:
            scan_labels = json.load(f)
        
        # Export labels
        export_yolo_labels(scan_labels, OUTPUT_DIR / 'labels' / 'val')
        
        # Copy images
        for face_data in scan_labels['faces'].values():
            src = IMAGES_DIR / face_data['image']
            dst = OUTPUT_DIR / 'images' / 'val' / face_data['image']
            shutil.copy(src, dst)
    
    # Create data.yaml for YOLO training
    yaml_content = f"""# RCubed Cube Sticker Dataset
path: {OUTPUT_DIR.absolute()}
train: images/train
val: images/val

# Classes
nc: 6  # number of classes
names: ['W', 'Y', 'R', 'O', 'B', 'G']  # class names
"""
    
    with open(OUTPUT_DIR / 'data.yaml', 'w') as f:
        f.write(yaml_content)
    
    print(f"\n✅ Export complete!")
    print(f"📁 Output: {OUTPUT_DIR.absolute()}")
    print(f"🎯 Train images: {len(train_files) * 6}")
    print(f"🎯 Val images: {len(val_files) * 6}")
    print(f"📄 Config: {OUTPUT_DIR / 'data.yaml'}")
    print("\n🚀 Ready for YOLOv8 training!")
    print(f"   yolo train model=yolov8n.pt data={OUTPUT_DIR / 'data.yaml'} epochs=50")

if __name__ == '__main__':
    main()
