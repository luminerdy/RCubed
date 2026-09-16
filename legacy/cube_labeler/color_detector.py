#!/usr/bin/env python3
"""
OpenCV-based sticker color detection for Rubik's cube faces.
Optimized for blue LED lighting environment.
"""

import cv2
import numpy as np
from pathlib import Path
import json

class StickerDetector:
    """Detect Rubik's cube sticker colors from face images."""
    
    # Face region bounds (from testing: x=180-460, y=75-400)
    # NOTE: Images are now pre-cropped by scan_6faces.py, so these bounds
    # are kept for reference but not used for cropping
    FACE_BOUNDS = {
        'x_min': 180,
        'x_max': 460,
        'y_min': 75,
        'y_max': 400
    }
    
    # Default color reference values (BGR format for OpenCV)
    # These are initial guesses - will be calibrated
    DEFAULT_COLOR_REFS = {
        'W': [220, 220, 220],  # White
        'Y': [100, 200, 220],  # Yellow (under blue LED)
        'R': [50, 50, 200],    # Red
        'O': [50, 150, 220],   # Orange
        'B': [200, 100, 50],   # Blue
        'G': [100, 150, 50]    # Green
    }
    
    def __init__(self, config_path='data/config.json'):
        """Initialize with optional calibration config."""
        self.config_path = Path(config_path)
        self.color_refs = self.DEFAULT_COLOR_REFS.copy()
        self.load_calibration()
    
    def load_calibration(self):
        """Load color calibration from config file if it exists."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    if 'color_refs' in config:
                        self.color_refs = config['color_refs']
                        print(f"✓ Loaded calibration from {self.config_path}")
            except Exception as e:
                print(f"Warning: Could not load calibration: {e}")
    
    def save_calibration(self, color_samples):
        """
        Save color calibration based on a solved cube scan.
        
        Args:
            color_samples: dict mapping color labels to list of BGR samples
                          e.g. {'W': [[220,220,220], [215,218,222], ...], ...}
        """
        # Average all samples for each color
        calibrated_refs = {}
        for color, samples in color_samples.items():
            if samples:
                avg = np.mean(samples, axis=0).tolist()
                calibrated_refs[color] = [int(v) for v in avg]
        
        config = {
            'color_refs': calibrated_refs,
            'calibrated': True
        }
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        self.color_refs = calibrated_refs
        print(f"✓ Saved calibration to {self.config_path}")
    
    def extract_face_region(self, image):
        """
        Extract face region from image.
        NOTE: Images from scan_6faces.py are already cropped, so just return as-is.
        Legacy function kept for compatibility.
        """
        # Images are now saved pre-cropped by scan_6faces.py
        return image
    
    def get_sticker_grid(self, face_img):
        """
        Divide face into 3×3 grid and return center points.
        
        Returns:
            tuple: (list of (x,y) centers, (width, height) of each sticker)
        """
        h, w = face_img.shape[:2]
        sticker_w = w // 3
        sticker_h = h // 3
        
        grid_centers = []
        for row in range(3):
            for col in range(3):
                # Center point of each sticker
                cx = col * sticker_w + sticker_w // 2
                cy = row * sticker_h + sticker_h // 2
                grid_centers.append((cx, cy))
        
        return grid_centers, (sticker_w, sticker_h)
    
    def sample_sticker_color(self, face_img, center, size):
        """
        Sample average color from center of sticker region.
        
        Args:
            face_img: Face region image
            center: (x, y) center point
            size: (width, height) of sticker
            
        Returns:
            numpy array: Average BGR color
        """
        cx, cy = center
        w, h = size
        
        # Sample from center 50% of sticker (avoid edges/shadows)
        sample_w = int(w * 0.5)
        sample_h = int(h * 0.5)
        
        x1 = max(0, cx - sample_w // 2)
        x2 = min(face_img.shape[1], cx + sample_w // 2)
        y1 = max(0, cy - sample_h // 2)
        y2 = min(face_img.shape[0], cy + sample_h // 2)
        
        region = face_img[y1:y2, x1:x2]
        
        # Average color in BGR
        avg_color = region.mean(axis=0).mean(axis=0)
        return avg_color
    
    def color_distance(self, c1, c2):
        """Euclidean distance between two colors in BGR space."""
        return np.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))
    
    def classify_color(self, bgr_color):
        """
        Map BGR color to nearest W/Y/R/O/B/G.
        
        Args:
            bgr_color: BGR color value (numpy array or list)
            
        Returns:
            str: Single letter color code
        """
        distances = {
            color: self.color_distance(bgr_color, ref)
            for color, ref in self.color_refs.items()
        }
        return min(distances, key=distances.get)
    
    def detect_face(self, image_path):
        """
        Detect all 9 sticker colors from a face image.
        
        Args:
            image_path: Path to face image file
            
        Returns:
            list: 9 color labels in reading order (top-left to bottom-right)
        """
        # Load image
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Extract face region
        face = self.extract_face_region(img)
        
        # Get 3×3 grid
        centers, size = self.get_sticker_grid(face)
        
        # Detect each sticker
        colors = []
        for center in centers:
            avg_color = self.sample_sticker_color(face, center, size)
            color_label = self.classify_color(avg_color)
            colors.append(color_label)
        
        return colors
    
    def detect_as_string(self, image_path):
        """Detect and return as 9-character string (e.g., 'GRYGWWWBB')."""
        colors = self.detect_face(image_path)
        return ''.join(colors)
    
    def detect_as_grid(self, image_path):
        """Detect and return as 3×3 grid array."""
        colors = self.detect_face(image_path)
        return [
            colors[0:3],
            colors[3:6],
            colors[6:9]
        ]
    
    def is_calibrated(self):
        """Check if detector has been calibrated."""
        return self.config_path.exists()
