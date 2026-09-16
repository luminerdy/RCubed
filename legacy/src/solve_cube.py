#!/usr/bin/env python3
"""
RCubed Cube Solver Pipeline
1. Read 6 face images from scans/
2. Detect sticker colors using k-means clustering across all 6 faces
3. Apply rotation corrections per face
4. Build Kociemba 54-char string
5. Solve

Face orientation corrections (from scan choreography):
  F, B, R, L = no rotation
  U = 90° CW
  D = 90° CCW
"""

import os
import sys
import cv2
import numpy as np
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SCAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scans")

# ─── Cube region in camera image ────────────────────────────────────────────
# Based on actual camera framing analysis
CUBE_BOUNDS = {
    'x1': 180, 'x2': 460,
    'y1': 75,  'y2': 400,
}

# ─── Rotation helpers ───────────────────────────────────────────────────────

def rotate_cw(grid):
    return [[grid[2][0], grid[1][0], grid[0][0]],
            [grid[2][1], grid[1][1], grid[0][1]],
            [grid[2][2], grid[1][2], grid[0][2]]]

def rotate_ccw(grid):
    return [[grid[0][2], grid[1][2], grid[2][2]],
            [grid[0][1], grid[1][1], grid[2][1]],
            [grid[0][0], grid[1][0], grid[2][0]]]

def flatten(grid):
    return [c for row in grid for c in row]

# ─── Scan to Kociemba face mapping ──────────────────────────────────────────

SCAN_TO_FACE = {
    'face_1_front.jpg': ('F', 'none'),
    'face_2_back.jpg':  ('B', 'none'),
    'face_3_right.jpg': ('R', 'none'),
    'face_4_left.jpg':  ('L', 'none'),
    'face_5_top.jpg':   ('U', 'cw'),
    'face_6_bottom.jpg':('D', 'ccw'),
}


def apply_rotation(grid, rot):
    if rot == 'cw': return rotate_cw(grid)
    if rot == 'ccw': return rotate_ccw(grid)
    if rot == '180': return rotate_cw(rotate_cw(grid))
    return grid


# ─── Extract sticker colors ─────────────────────────────────────────────────

def extract_sticker_colors(image_path):
    """Extract mean LAB color for each of 9 stickers. Returns list of 9 LAB values."""
    img = cv2.imread(image_path)
    if img is None:
        return None
    
    h, w = img.shape[:2]
    
    # Crop to cube region
    x1, x2 = CUBE_BOUNDS['x1'], CUBE_BOUNDS['x2']
    y1, y2 = CUBE_BOUNDS['y1'], CUBE_BOUNDS['y2']
    
    # Clamp to image bounds
    x1, x2 = max(0, x1), min(w, x2)
    y1, y2 = max(0, y1), min(h, y2)
    
    cube = img[y1:y2, x1:x2]
    lab = cv2.cvtColor(cube, cv2.COLOR_BGR2LAB)
    
    ch, cw = cube.shape[:2]
    cell_h = ch // 3
    cell_w = cw // 3
    
    # Sample center 40% of each cell to avoid sticker borders
    pad_h = int(cell_h * 0.3)
    pad_w = int(cell_w * 0.3)
    
    colors = []
    for row in range(3):
        for col in range(3):
            sy1 = row * cell_h + pad_h
            sy2 = (row + 1) * cell_h - pad_h
            sx1 = col * cell_w + pad_w
            sx2 = (col + 1) * cell_w - pad_w
            
            patch = lab[sy1:sy2, sx1:sx2]
            mean_color = patch.reshape(-1, 3).mean(axis=0)
            colors.append(mean_color)
    
    return colors


def cluster_colors(all_colors):
    """
    Use k-means to cluster 54 sticker colors into 6 groups.
    Returns cluster labels (0-5) for each sticker.
    """
    data = np.array(all_colors, dtype=np.float32)
    
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, centers = cv2.kmeans(data, 6, None, criteria, 20, cv2.KMEANS_PP_CENTERS)
    
    return labels.flatten(), centers


def assign_cluster_to_face(labels, face_stickers_map):
    """
    The center sticker (index 4) of each face defines its cluster.
    Map cluster IDs to face letters.
    
    Center stickers are hardcoded to avoid issues with the Rubik's logo
    on the white center (multicolor logo confuses k-means).
    """
    cluster_to_face = {}
    for face_letter, sticker_indices in face_stickers_map.items():
        center_idx = sticker_indices[4]  # center sticker
        # Hardcode: center always belongs to its own face
        labels[center_idx] = -1  # mark as special
        cluster_id = labels[center_idx]
    
    # Instead of using cluster IDs from centers, assign each non-center
    # sticker to the nearest face by comparing to the 6 known center colors.
    # But since we hardcode centers, we just force center labels.
    
    # Reset: use cluster detection for non-centers, but force centers
    # We need a different approach — assign clusters by proximity to
    # the majority of stickers, but force center identity.
    
    # Simple approach: for each face, the center IS that face letter.
    # For all other stickers, find which center color they're closest to.
    return cluster_to_face


def assign_stickers_by_nearest_center(all_colors, face_stickers_map):
    """
    Assign each sticker to the nearest face center color (in LAB space).
    Centers are hardcoded — each face's center sticker IS that face.
    This avoids issues with the Rubik's logo on the white center.
    """
    # Get the center color for each face
    center_colors = {}
    for face_letter, indices in face_stickers_map.items():
        center_colors[face_letter] = all_colors[indices[4]]
    
    print(f"  Center colors (LAB):")
    for face, color in center_colors.items():
        print(f"    {face}: L={color[0]:.0f} A={color[1]:.0f} B={color[2]:.0f}")
    
    # Assign every sticker to the nearest center
    face_order = list(center_colors.keys())
    center_array = np.array([center_colors[f] for f in face_order])
    
    assignments = []
    for i, color in enumerate(all_colors):
        dists = np.linalg.norm(center_array - np.array(color), axis=1)
        nearest = face_order[np.argmin(dists)]
        assignments.append(nearest)
    
    # Force centers to their own face (in case logo skewed them)
    for face_letter, indices in face_stickers_map.items():
        assignments[indices[4]] = face_letter
    
    return assignments


def save_debug_image(image_path, face_name, sticker_labels, cluster_to_face):
    """Save debug image with detected colors overlaid."""
    img = cv2.imread(image_path)
    x1, x2 = CUBE_BOUNDS['x1'], CUBE_BOUNDS['x2']
    y1, y2 = CUBE_BOUNDS['y1'], CUBE_BOUNDS['y2']
    
    h, w = img.shape[:2]
    x1, x2 = max(0, x1), min(w, x2)
    y1, y2 = max(0, y1), min(h, y2)
    
    ch = y2 - y1
    cw_px = x2 - x1
    cell_h = ch // 3
    cell_w = cw_px // 3
    
    color_bgr = {
        'U': (0, 128, 255), 'R': (255, 100, 0), 'F': (255, 255, 255),
        'D': (0, 0, 255), 'L': (0, 200, 0), 'B': (0, 255, 255),
    }
    
    for i, label in enumerate(sticker_labels):
        row, col = divmod(i, 3)
        face_letter = cluster_to_face.get(label, '?')
        
        cx = x1 + col * cell_w + cell_w // 2
        cy = y1 + row * cell_h + cell_h // 2
        
        bgr = color_bgr.get(face_letter, (128, 128, 128))
        cv2.circle(img, (cx, cy), 15, bgr, -1)
        cv2.putText(img, face_letter, (cx - 8, cy + 6),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    
    debug_path = os.path.join(SCAN_DIR, f"debug_{face_name}.jpg")
    cv2.imwrite(debug_path, img)


# ─── Main Pipeline ──────────────────────────────────────────────────────────

def scan_and_solve(debug=True):
    """Full pipeline: read images → detect colors → solve."""
    
    print("═══ STEP 1: EXTRACTING STICKER COLORS ═══")
    
    # Collect all 54 sticker colors in order: U, R, F, D, L, B
    face_order = ['U', 'R', 'F', 'D', 'L', 'B']
    
    # Map filename → face letter and rotation
    face_data = {}  # face_letter → (filename, rotation)
    for fname, (face_letter, rotation) in SCAN_TO_FACE.items():
        face_data[face_letter] = (fname, rotation)
    
    all_colors = []  # 54 LAB colors
    face_stickers_map = {}  # face_letter → [global indices of its 9 stickers]
    face_grids_raw = {}  # face_letter → raw 3x3 grid indices (before rotation)
    
    global_idx = 0
    for face in face_order:
        fname, rotation = face_data[face]
        filepath = os.path.join(SCAN_DIR, fname)
        
        if not os.path.exists(filepath):
            print(f"  ❌ Missing: {filepath}")
            return None
        
        colors = extract_sticker_colors(filepath)
        if colors is None:
            print(f"  ❌ Could not read: {filepath}")
            return None
        
        # Apply rotation correction to the color order
        grid = [colors[0:3], colors[3:6], colors[6:9]]
        grid = apply_rotation(grid, rotation)
        corrected_colors = flatten(grid)
        
        indices = list(range(global_idx, global_idx + 9))
        face_stickers_map[face] = indices
        
        all_colors.extend(corrected_colors)
        global_idx += 9
        
        print(f"  {face} ({fname}): extracted 9 stickers")
    
    print(f"\n  Total stickers: {len(all_colors)}")
    
    # ── Step 2: Assign stickers by nearest center color ──
    print("\n═══ STEP 2: ASSIGNING COLORS BY NEAREST CENTER ═══")
    assignments = assign_stickers_by_nearest_center(all_colors, face_stickers_map)
    
    # ── Step 3: Build Kociemba string ──
    print("\n═══ STEP 3: BUILDING KOCIEMBA STRING ═══")
    cube_string = "".join(assignments)
    
    print(f"  Cube string: {cube_string}")
    
    # Validate
    counts = Counter(cube_string)
    print(f"  Counts: {dict(counts)}")
    
    if any(v != 9 for v in counts.values()) or len(counts) != 6:
        print("  ⚠️  Unbalanced colors — detection issue")
    
    # ── Save debug images ──
    if debug:
        print("\n═══ SAVING DEBUG IMAGES ═══")
        for face in face_order:
            fname, rotation = face_data[face]
            filepath = os.path.join(SCAN_DIR, fname)
            indices = face_stickers_map[face]
            face_assignments = [assignments[i] for i in indices]
            
            # Save debug image with face letters overlaid
            img = cv2.imread(filepath)
            x1, x2 = CUBE_BOUNDS['x1'], CUBE_BOUNDS['x2']
            y1, y2 = CUBE_BOUNDS['y1'], CUBE_BOUNDS['y2']
            h, w = img.shape[:2]
            x1, x2 = max(0, x1), min(w, x2)
            y1, y2 = max(0, y1), min(h, y2)
            ch = y2 - y1
            cw_px = x2 - x1
            cell_h = ch // 3
            cell_w = cw_px // 3
            color_bgr = {
                'U': (0, 128, 255), 'R': (255, 100, 0), 'F': (255, 255, 255),
                'D': (0, 0, 255), 'L': (0, 200, 0), 'B': (0, 255, 255),
            }
            for i, fl in enumerate(face_assignments):
                row, col = divmod(i, 3)
                cx = x1 + col * cell_w + cell_w // 2
                cy = y1 + row * cell_h + cell_h // 2
                bgr = color_bgr.get(fl, (128, 128, 128))
                cv2.circle(img, (cx, cy), 15, bgr, -1)
                cv2.putText(img, fl, (cx - 8, cy + 6),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            debug_path = os.path.join(SCAN_DIR, f"debug_{face}.jpg")
            cv2.imwrite(debug_path, img)
            
            face_str = "".join(face_assignments)
            print(f"  {face}: {face_str[:3]} {face_str[3:6]} {face_str[6:9]}")
    
    # ── Step 4: Solve ──
    print(f"\n═══ STEP 4: SOLVING ═══")
    try:
        import kociemba
        solution = kociemba.solve(cube_string)
        print(f"  ✅ Solution: {solution}")
        return solution
    except Exception as e:
        print(f"  ❌ Solver error: {e}")
        print("  Color detection likely has errors. Try adjusting lighting or camera angle.")
        return None


def test_manual():
    """Test with Scotty's manually verified readings."""
    print("═══ TESTING WITH MANUAL READINGS ═══\n")
    
    raw = {
        'F': [['O','W','G'], ['R','W','R'], ['B','B','O']],
        'B': [['R','B','B'], ['W','Y','O'], ['B','G','Y']],
        'R': [['R','Y','Y'], ['W','B','B'], ['W','B','B']],
        'L': [['W','G','G'], ['G','G','G'], ['R','Y','Y']],
        'U': [['G','R','W'], ['R','O','O'], ['R','Y','Y']],
        'D': [['B','O','R'], ['W','R','Y'], ['O','O','G']],
    }
    
    corrections = {'F': 'none', 'B': 'none', 'R': 'none', 'L': 'none', 'U': 'cw', 'D': 'ccw'}
    
    faces = {}
    for face, grid in raw.items():
        corrected = apply_rotation(grid, corrections[face])
        stickers = flatten(corrected)
        faces[face] = stickers
        print(f"  {face}: {stickers[:3]} / {stickers[3:6]} / {stickers[6:9]}")
    
    all_stickers = []
    for face in ['U', 'R', 'F', 'D', 'L', 'B']:
        all_stickers.extend(faces[face])
    counts = Counter(all_stickers)
    print(f"\n  Color counts: {dict(counts)}")
    
    # Map colors to face letters
    color_to_face = {}
    for face in ['U', 'R', 'F', 'D', 'L', 'B']:
        center = faces[face][4]
        color_to_face[center] = face
    
    print(f"  Color→Face: {color_to_face}")
    
    cube_string = ""
    for face in ['U', 'R', 'F', 'D', 'L', 'B']:
        for color in faces[face]:
            cube_string += color_to_face.get(color, '?')
    
    print(f"  Cube string: {cube_string}")
    
    try:
        import kociemba
        solution = kociemba.solve(cube_string)
        print(f"\n  ✅ SOLUTION: {solution}")
    except Exception as e:
        print(f"\n  ❌ Solver error: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RCubed Cube Solver")
    parser.add_argument('--manual', action='store_true', help='Test with manual readings')
    parser.add_argument('--no-debug', action='store_true', help='Skip debug images')
    args = parser.parse_args()
    
    if args.manual:
        test_manual()
    else:
        scan_and_solve(debug=not args.no_debug)
