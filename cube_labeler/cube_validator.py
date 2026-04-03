#!/usr/bin/env python3
"""
Cube validation for training data.
Checks if a labeled cube represents a valid physical cube state.
Uses center colors to determine Kociemba face mapping.
"""

try:
    import kociemba
except ImportError:
    import subprocess
    import sys
    print("Installing kociemba...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "kociemba"])
    import kociemba

# Standard cube center mapping: color → Kociemba face
# On a standard solved cube:
#   F (Front) = White, B (Back) = Yellow
#   R (Right) = Red, L (Left) = Orange
#   U (Up/Top) = Blue, D (Down/Bottom) = Green
CENTER_TO_FACE = {
    'W': 'F',  # White → Front
    'Y': 'B',  # Yellow → Back
    'R': 'R',  # Red → Right
    'O': 'L',  # Orange → Left
    'B': 'U',  # Blue → Up
    'G': 'D',  # Green → Down
}

def validate_cube_state(faces_dict):
    """
    Validate a cube state by checking all possible orientations.
    
    Args:
        faces_dict: Dict with keys 'front', 'back', 'right', 'left', 'top', 'bottom'
                   Each value is a dict with 'grid' (3x3 list of color letters)
    
    Returns:
        dict with keys:
            - valid: bool
            - centers_unique: bool
            - color_counts_valid: bool
            - solvable: bool
            - error: str (if not valid)
            - solution: str (if solvable)
    """
    result = {
        'valid': False,
        'centers_unique': False,
        'color_counts_valid': False,
        'solvable': False,
        'error': None,
        'solution': None
    }
    
    # Extract grids in order: front, back, right, left, top, bottom
    try:
        grids = [
            faces_dict['front']['grid'],
            faces_dict['back']['grid'],
            faces_dict['right']['grid'],
            faces_dict['left']['grid'],
            faces_dict['top']['grid'],
            faces_dict['bottom']['grid'],
        ]
    except KeyError as e:
        result['error'] = f"Missing face: {e}"
        return result
    
    # Check 1: Validate grid structure
    for i, grid in enumerate(grids):
        if len(grid) != 3:
            result['error'] = f"Face {i}: expected 3 rows, got {len(grid)}"
            return result
        for j, row in enumerate(grid):
            if len(row) != 3:
                result['error'] = f"Face {i} row {j}: expected 3 cols, got {len(row)}"
                return result
    
    # Check 2: Count colors
    color_counts = {}
    centers = []
    for grid in grids:
        for i, row in enumerate(grid):
            for j, color in enumerate(row):
                color_counts[color] = color_counts.get(color, 0) + 1
                if i == 1 and j == 1:
                    centers.append(color)
    
    # Check 2a: Must have exactly 9 of each color
    expected_colors = ['W', 'Y', 'R', 'O', 'B', 'G']
    for color in expected_colors:
        count = color_counts.get(color, 0)
        if count != 9:
            result['error'] = f"Color {color}: expected 9, got {count}"
            return result
    
    for color in color_counts:
        if color not in expected_colors:
            result['error'] = f"Unexpected color: {color}"
            return result
    
    result['color_counts_valid'] = True
    
    # Check 2b: All centers must be different
    if len(set(centers)) != 6:
        result['error'] = f"Centers must be 6 different colors, got: {centers}"
        return result
    
    result['centers_unique'] = True
    
    # Check 3: Use center colors to determine Kociemba mapping
    # Build a dict: Kociemba face → grid
    face_to_grid = {}
    
    for grid in grids:
        center_color = grid[1][1]
        if center_color not in CENTER_TO_FACE:
            result['error'] = f"Unknown center color: {center_color}"
            return result
        
        kociemba_face = CENTER_TO_FACE[center_color]
        face_to_grid[kociemba_face] = grid
    
    # Verify we have all 6 faces
    if len(face_to_grid) != 6:
        result['error'] = f"Expected 6 Kociemba faces, got {len(face_to_grid)}"
        return result
    
    # Build Kociemba string in order: U R F D L B
    kociemba_str = ""
    for face in ['U', 'R', 'F', 'D', 'L', 'B']:
        grid = face_to_grid[face]
        for row in grid:
            for color in row:
                # Map color to Kociemba face letter using centers
                kociemba_str += CENTER_TO_FACE[color]
    
    # Try to solve
    try:
        solution = kociemba.solve(kociemba_str)
        # Valid solution found!
        result['valid'] = True
        result['solvable'] = True
        result['solution'] = solution
        return result
    except Exception as e:
        # Kociemba failed - cube state is invalid
        result['error'] = f"Invalid cube state: {str(e)}"
        return result
