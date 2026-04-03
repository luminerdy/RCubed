#!/usr/bin/env python3
"""
RCubed Autonomous Solver
Full pipeline: Scan → Vision API read → Kociemba solve → Execute

Usage:
  python3 auto_solve.py              # Full solve
  python3 auto_solve.py --scan-only  # Just scan and show solution
  python3 auto_solve.py --dry-run    # Scan, read, solve, but don't execute
"""

import sys
import os
import time
import json
import base64
import cv2
import subprocess
from collections import Counter

sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import maestro
import anthropic
import kociemba

# ─── Config ──────────────────────────────────────────────────────────────────

SCAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scans")
MAESTRO_PORT = '/dev/ttyACM0'
MAESTRO_PORT_ALT = '/dev/ttyACM1'

# Cube region in camera image
CUBE_BOUNDS = {'x1': 180, 'x2': 460, 'y1': 75, 'y2': 400}

# Rotation corrections from scan choreography
ROTATION_CORRECTIONS = {
    'F': 'none', 'B': 'none', 'R': 'none',
    'L': 'none', 'U': 'cw', 'D': 'ccw'
}

VISION_PROMPT = (
    "This is a cropped photo of a Rubik's cube face showing a 3x3 grid of colored stickers. "
    "Identify each sticker color reading left-to-right, top-to-bottom. "
    "The 6 possible colors are: Red (R), Orange (O), Yellow (Y), Green (G), Blue (B), White (W). "
    "Be very careful distinguishing Orange from Yellow — Orange is darker/warmer, Yellow is lighter/brighter. "
    "Also distinguish Red (deep/dark) from Orange (lighter/warmer). "
    "Reply ONLY with 9 color letters separated by spaces, like: R O Y G B W R O Y"
)

# ─── API Key ─────────────────────────────────────────────────────────────────

def get_api_key():
    """Get Anthropic API key from environment or OpenClaw auth store."""
    key = os.environ.get('ANTHROPIC_API_KEY')
    if key:
        return key
    
    auth_path = os.path.expanduser('~/.openclaw/agents/main/agent/auth-profiles.json')
    try:
        with open(auth_path) as f:
            data = json.load(f)
        return data['profiles']['anthropic:default']['token']
    except (FileNotFoundError, KeyError):
        pass
    
    print("❌ No Anthropic API key found!")
    print("   Set ANTHROPIC_API_KEY env var or ensure OpenClaw auth is configured.")
    sys.exit(1)

# ─── Maestro Port Detection ─────────────────────────────────────────────────

def find_maestro_port():
    """Find the Maestro serial port."""
    for port in [MAESTRO_PORT, MAESTRO_PORT_ALT]:
        if os.path.exists(port):
            return port
    print("❌ Maestro not found on ttyACM0 or ttyACM1!")
    sys.exit(1)

# ─── Rotation Helpers ────────────────────────────────────────────────────────

def rotate_cw(g):
    return [g[6],g[3],g[0], g[7],g[4],g[1], g[8],g[5],g[2]]

def rotate_ccw(g):
    return [g[2],g[5],g[8], g[1],g[4],g[7], g[0],g[3],g[6]]

def apply_rotation(stickers, rot):
    if rot == 'cw': return rotate_cw(stickers)
    if rot == 'ccw': return rotate_ccw(stickers)
    return stickers

# ─── Vision API ──────────────────────────────────────────────────────────────

def crop_and_encode(image_path):
    """Crop cube region, upscale, and return base64 JPEG."""
    img = cv2.imread(image_path)
    if img is None:
        return None
    x1, x2 = CUBE_BOUNDS['x1'], CUBE_BOUNDS['x2']
    y1, y2 = CUBE_BOUNDS['y1'], CUBE_BOUNDS['y2']
    crop = img[y1:y2, x1:x2]
    crop = cv2.resize(crop, (crop.shape[1]*2, crop.shape[0]*2), interpolation=cv2.INTER_CUBIC)
    _, buf = cv2.imencode('.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return base64.standard_b64encode(buf).decode('utf-8')

def read_face_colors(client, image_b64):
    """Send cropped face image to Claude vision API and get 9 color letters."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_b64,
                    }
                },
                {
                    "type": "text",
                    "text": VISION_PROMPT
                }
            ]
        }]
    )
    text = response.content[0].text.strip()
    colors = text.split()
    if len(colors) != 9:
        raise ValueError(f"Expected 9 colors, got {len(colors)}: {text}")
    valid = set('ROYGBW')
    for c in colors:
        if c not in valid:
            raise ValueError(f"Invalid color '{c}' in: {text}")
    return colors

# ─── Scan ────────────────────────────────────────────────────────────────────

def scan_cube(port):
    """Run full_solve.py scan choreography. Returns when scan is complete."""
    print("\n═══ STEP 1: SCANNING CUBE ═══")
    result = subprocess.run(
        ['python3', 'full_solve.py'],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        print(f"❌ Scan failed: {result.stderr}")
        sys.exit(1)
    print(result.stdout)
    
    # Verify all 6 images exist
    face_files = [
        'face_1_front.jpg', 'face_2_back.jpg', 'face_3_right.jpg',
        'face_4_left.jpg', 'face_5_top.jpg', 'face_6_bottom.jpg'
    ]
    for f in face_files:
        if not os.path.exists(os.path.join(SCAN_DIR, f)):
            print(f"❌ Missing scan image: {f}")
            sys.exit(1)
    print("  ✅ All 6 face images captured")

# ─── Color Reading ───────────────────────────────────────────────────────────

def read_all_faces(client):
    """Read colors from all 6 face images using vision API."""
    print("\n═══ STEP 2: READING COLORS (Vision API) ═══")
    
    face_map = {
        'face_1_front.jpg': 'F',
        'face_2_back.jpg': 'B',
        'face_3_right.jpg': 'R',
        'face_4_left.jpg': 'L',
        'face_5_top.jpg': 'U',
        'face_6_bottom.jpg': 'D',
    }
    
    faces_raw = {}
    for filename, face_letter in face_map.items():
        filepath = os.path.join(SCAN_DIR, filename)
        b64 = crop_and_encode(filepath)
        if b64 is None:
            print(f"  ❌ Could not read {filename}")
            sys.exit(1)
        
        colors = read_face_colors(client, b64)
        faces_raw[face_letter] = colors
        print(f"  {face_letter} ({filename}): {' '.join(colors)}")
    
    return faces_raw

# ─── Solve ───────────────────────────────────────────────────────────────────

def build_kociemba_string(faces_raw):
    """Apply rotations, validate, and build Kociemba string."""
    print("\n═══ STEP 3: BUILDING KOCIEMBA STRING ═══")
    
    # Apply rotation corrections
    faces = {}
    for f, raw in faces_raw.items():
        faces[f] = apply_rotation(raw, ROTATION_CORRECTIONS[f])
    
    # Get centers → color-to-face mapping
    color_to_face = {}
    for f in faces:
        center = faces[f][4]
        if center in color_to_face:
            print(f"  ❌ Duplicate center color {center} on faces {color_to_face[center]} and {f}")
            return None
        color_to_face[center] = f
    
    print(f"  Centers: {', '.join(f'{f}={faces[f][4]}' for f in ['U','R','F','D','L','B'])}")
    print(f"  Color→Face: {color_to_face}")
    
    # Count colors
    all_colors = []
    for f in faces:
        all_colors.extend(faces[f])
    counts = Counter(all_colors)
    print(f"  Counts: {dict(counts)}")
    
    if len(color_to_face) != 6:
        print(f"  ❌ Only {len(color_to_face)} unique centers (need 6)")
        return None
    
    if all(v == 9 for v in counts.values()):
        print("  ✅ All colors balanced (9 each)")
    else:
        # Try O↔R swap fix (most common misread)
        print("  ⚠️  Colors unbalanced — attempting O↔R correction...")
        solution = try_swap_fix(faces_raw, faces, color_to_face)
        if solution:
            return solution
        print("  ❌ Could not auto-correct color readings")
        return None
    
    # Build string
    cube_str = ''
    for f in ['U', 'R', 'F', 'D', 'L', 'B']:
        for c in faces[f]:
            cube_str += color_to_face.get(c, '?')
    
    print(f"  Kociemba string: {cube_str}")
    return cube_str

def try_swap_fix(faces_raw, faces, color_to_face):
    """Try single-sticker O↔R swaps to find a valid cube state."""
    swap_pairs = [('O', 'R'), ('R', 'O'), ('Y', 'O'), ('O', 'Y'), ('Y', 'R'), ('R', 'Y')]
    
    for from_c, to_c in swap_pairs:
        for face_name in ['F', 'B', 'R', 'L', 'U', 'D']:
            raw = list(faces_raw[face_name])
            for i in range(9):
                if raw[i] == from_c:
                    raw[i] = to_c
                    test_raw = dict(faces_raw)
                    test_raw[face_name] = raw
                    
                    # Apply rotations
                    test_faces = {}
                    for f, r in test_raw.items():
                        test_faces[f] = apply_rotation(list(r), ROTATION_CORRECTIONS[f])
                    
                    # Check centers unique
                    ctf = {}
                    ok = True
                    for f in test_faces:
                        c = test_faces[f][4]
                        if c in ctf:
                            ok = False
                            break
                        ctf[c] = f
                    if not ok or len(ctf) != 6:
                        raw[i] = from_c
                        continue
                    
                    # Check counts
                    all_c = []
                    for f in test_faces:
                        all_c.extend(test_faces[f])
                    if any(Counter(all_c)[x] != 9 for x in ctf.keys()):
                        raw[i] = from_c
                        continue
                    
                    # Build string and try solve
                    cube_str = ''
                    for f in ['U', 'R', 'F', 'D', 'L', 'B']:
                        for c in test_faces[f]:
                            cube_str += ctf.get(c, '?')
                    if '?' in cube_str:
                        raw[i] = from_c
                        continue
                    
                    try:
                        sol = kociemba.solve(cube_str)
                        print(f"  ✅ Fixed: {face_name} pos {i}: {from_c}→{to_c}")
                        print(f"  Kociemba string: {cube_str}")
                        return cube_str
                    except:
                        pass
                    
                    raw[i] = from_c
    return None

def solve_cube(cube_str):
    """Run Kociemba solver."""
    print("\n═══ STEP 4: SOLVING ═══")
    try:
        solution = kociemba.solve(cube_str)
        moves = solution.split()
        print(f"  ✅ Solution: {solution}")
        print(f"  Moves: {len(moves)}")
        return solution
    except Exception as e:
        print(f"  ❌ Solver error: {e}")
        return None

# ─── Execute ─────────────────────────────────────────────────────────────────

def execute_solution(solution, port):
    """Run move_executor.py with the solution."""
    print(f"\n═══ STEP 5: EXECUTING SOLUTION ═══")
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'move_executor.py')
    result = subprocess.run(
        ['python3', script, '--port', port, solution],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        timeout=600
    )
    if result.returncode != 0:
        print(f"  ❌ Execution failed (code {result.returncode})")
        return False
    return True

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="RCubed Autonomous Solver")
    parser.add_argument('--scan-only', action='store_true', help='Scan and read only, no solve/execute')
    parser.add_argument('--dry-run', action='store_true', help='Scan, read, solve — but do not execute')
    parser.add_argument('--no-scan', action='store_true', help='Skip scan, use existing images')
    parser.add_argument('--port', default=None, help='Maestro port override')
    args = parser.parse_args()
    
    print("🎲 RCubed Autonomous Solver")
    print("=" * 50)
    
    # Setup
    port = args.port or find_maestro_port()
    api_key = get_api_key()
    client = anthropic.Anthropic(api_key=api_key)
    
    print(f"  Maestro: {port}")
    print(f"  API: Anthropic Claude (vision)")
    
    # Step 1: Scan
    if not args.no_scan:
        scan_cube(port)
    else:
        print("\n═══ STEP 1: SKIPPING SCAN (using existing images) ═══")
    
    # Step 2: Read colors
    faces_raw = read_all_faces(client)
    
    # Step 3: Build Kociemba string
    cube_str = build_kociemba_string(faces_raw)
    if cube_str is None:
        print("\n❌ Could not build valid cube string. Check face images.")
        sys.exit(1)
    
    if args.scan_only:
        print("\n✅ Scan complete. Use --dry-run or full run to solve.")
        return
    
    # Step 4: Solve
    solution = solve_cube(cube_str)
    if solution is None:
        sys.exit(1)
    
    if args.dry_run:
        print(f"\n✅ Dry run complete. Solution: {solution}")
        return
    
    # Step 5: Execute
    success = execute_solution(solution, port)
    
    if success:
        print("\n🎲 ═══ CUBE SOLVED! ═══ 🎲")
    else:
        print("\n❌ Solve execution failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
