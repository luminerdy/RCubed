#!/usr/bin/env python3
"""
Flask web application for reviewing and confirming Rubik's cube color labels.
Updated to work with:
- training_scans/scan_NNN/face_N_name.jpg directory structure
- first_pass_labels.json for label storage
- confirmed_labels.json for tracking reviewed scans
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from pathlib import Path
import json
from collections import Counter

app = Flask(__name__)

# Paths - relative to cube_labeler directory
BASE_DIR = Path(__file__).parent.parent  # repo root
TRAINING_DIR = BASE_DIR / "training_scans"
LABELS_FILE = BASE_DIR / "first_pass_labels.json"
CONFIRMED_FILE = BASE_DIR / "confirmed_labels.json"

# Face name mapping
FACE_MAP = {
    'face_1_front': 'front',
    'face_2_back': 'back', 
    'face_3_right': 'right',
    'face_4_left': 'left',
    'face_5_top': 'top',
    'face_6_bottom': 'bottom'
}
FACE_FILES = ['face_1_front.jpg', 'face_2_back.jpg', 'face_3_right.jpg', 
              'face_4_left.jpg', 'face_5_top.jpg', 'face_6_bottom.jpg']

def load_labels():
    """Load labels from first_pass_labels.json"""
    if LABELS_FILE.exists():
        with open(LABELS_FILE) as f:
            return json.load(f)
    return {}

def save_labels(labels):
    """Save labels to first_pass_labels.json"""
    with open(LABELS_FILE, 'w') as f:
        json.dump(labels, f, indent=2)

def load_confirmed():
    """Load confirmed scan tracking"""
    if CONFIRMED_FILE.exists():
        with open(CONFIRMED_FILE) as f:
            return json.load(f)
    return {"confirmed": [], "reviewed_scans": []}

def save_confirmed(confirmed):
    """Save confirmed scan tracking"""
    with open(CONFIRMED_FILE, 'w') as f:
        json.dump(confirmed, f, indent=2)

def get_scan_list():
    """Get list of all scans from training_scans directory"""
    scans = []
    labels = load_labels()
    confirmed = load_confirmed()
    confirmed_scans = confirmed.get('reviewed_scans', [])
    
    # Find all scan directories
    if TRAINING_DIR.exists():
        for scan_dir in sorted(TRAINING_DIR.iterdir()):
            if scan_dir.is_dir() and scan_dir.name.startswith('scan_'):
                # Check if all 6 faces exist
                faces_exist = all((scan_dir / f).exists() for f in FACE_FILES)
                if faces_exist:
                    scan_name = scan_dir.name
                    # Extract numeric ID
                    try:
                        scan_id = int(scan_name.replace('scan_', ''))
                    except ValueError:
                        scan_id = 0
                    
                    scans.append({
                        'id': scan_id,
                        'name': scan_name,
                        'confirmed': scan_name in confirmed_scans,
                        'faces': FACE_FILES
                    })
    
    return scans

def get_scan_labels(scan_name):
    """Get labels for a specific scan, converting to face-based format"""
    labels = load_labels()
    result = {
        'scan_name': scan_name,
        'faces': {},
        'verified': False
    }
    
    for face_file in FACE_FILES:
        key = f"{scan_name}/{face_file}"
        face_name = FACE_MAP[face_file.replace('.jpg', '')]
        
        if key in labels:
            # Convert flat array to 3x3 grid
            flat = labels[key]
            grid = [flat[0:3], flat[3:6], flat[6:9]]
        else:
            # Default to unknown
            grid = [['?', '?', '?'], ['?', '?', '?'], ['?', '?', '?']]
        
        result['faces'][face_name] = {
            'image': face_file,
            'grid': grid
        }
    
    return result

def count_colors(faces):
    """Count colors across all faces"""
    counts = Counter()
    for face_data in faces.values():
        for row in face_data['grid']:
            counts.update(row)
    
    # Ensure all colors present
    for color in ['W', 'Y', 'R', 'O', 'B', 'G']:
        if color not in counts:
            counts[color] = 0
    
    return dict(counts)

@app.route('/')
def index():
    """Serve the labeling interface"""
    return render_template('index.html', calibrated=True)

@app.route('/api/scans')
def api_scans():
    """Return list of all scans with status"""
    scans = get_scan_list()
    confirmed_count = sum(1 for s in scans if s['confirmed'])
    return jsonify({
        'scans': scans,
        'total': len(scans),
        'confirmed': confirmed_count,
        'remaining': len(scans) - confirmed_count,
        'calibrated': True
    })

@app.route('/api/scan/<int:scan_id>')
def api_scan(scan_id):
    """Get scan data with labels for all 6 faces"""
    scan_name = f"scan_{scan_id:03d}"
    scan_dir = TRAINING_DIR / scan_name
    
    if not scan_dir.exists():
        return jsonify({'error': 'Scan not found'}), 404
    
    labels = get_scan_labels(scan_name)
    labels['color_counts'] = count_colors(labels['faces'])
    
    # Check if confirmed
    confirmed = load_confirmed()
    labels['verified'] = scan_name in confirmed.get('reviewed_scans', [])
    
    return jsonify(labels)

@app.route('/api/validate', methods=['POST'])
def api_validate():
    """Validate cube state"""
    data = request.json
    faces = data.get('faces', {})
    
    # Count colors
    counts = count_colors(faces)
    
    # Check constraints
    errors = []
    warnings = []
    
    # Each color should appear exactly 9 times
    for color, count in counts.items():
        if color in ['W', 'Y', 'R', 'O', 'B', 'G']:
            if count != 9:
                errors.append(f"{color}: {count} (should be 9)")
    
    # Check centers are unique
    centers = []
    for face_data in faces.values():
        grid = face_data['grid']
        centers.append(grid[1][1])  # Center is [1][1]
    
    if len(set(centers)) != 6:
        errors.append("Centers must be 6 different colors")
    
    return jsonify({
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'color_counts': counts
    })

@app.route('/api/delete', methods=['POST'])
def api_delete():
    """Delete a scan (images and labels)"""
    data = request.json
    scan_id = data['scan_id']
    scan_name = f"scan_{scan_id:03d}"
    
    # Remove from labels
    labels = load_labels()
    keys_to_remove = [k for k in labels if k.startswith(f"{scan_name}/")]
    for k in keys_to_remove:
        del labels[k]
    save_labels(labels)
    
    # Remove from confirmed
    confirmed = load_confirmed()
    if scan_name in confirmed.get('reviewed_scans', []):
        confirmed['reviewed_scans'].remove(scan_name)
    confirmed['confirmed'] = [c for c in confirmed.get('confirmed', []) if not c.startswith(f"{scan_name}/")]
    save_confirmed(confirmed)
    
    # Remove image directory
    scan_dir = TRAINING_DIR / scan_name
    if scan_dir.exists():
        import shutil
        shutil.rmtree(scan_dir)
    
    # Also remove old flat file format if exists
    for f in TRAINING_DIR.glob(f"{scan_name}_face_*.jpg"):
        f.unlink()
    
    return jsonify({'status': 'deleted', 'scan': scan_name})

@app.route('/api/save', methods=['POST'])
def api_save():
    """Save labels for a scan"""
    data = request.json
    scan_id = data['scan_id']
    scan_name = f"scan_{scan_id:03d}"
    faces = data['faces']
    
    # Load current labels
    labels = load_labels()
    
    # Convert grid format back to flat arrays and save
    for face_name, face_data in faces.items():
        # Find the file name for this face
        for file_key, name in FACE_MAP.items():
            if name == face_name:
                key = f"{scan_name}/{file_key}.jpg"
                # Flatten grid to array
                flat = []
                for row in face_data['grid']:
                    flat.extend(row)
                labels[key] = flat
                break
    
    save_labels(labels)
    
    # Mark as confirmed
    confirmed = load_confirmed()
    if scan_name not in confirmed['reviewed_scans']:
        confirmed['reviewed_scans'].append(scan_name)
    
    # Track individual images
    for face_file in FACE_FILES:
        key = f"{scan_name}/{face_file}"
        if key not in confirmed['confirmed']:
            confirmed['confirmed'].append(key)
    
    save_confirmed(confirmed)
    
    return jsonify({'status': 'ok', 'confirmed': True})

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve image files from training_scans directory"""
    # filename format: scan_NNN/face_N_name.jpg
    parts = filename.split('/')
    if len(parts) == 2:
        scan_name, face_file = parts
        scan_dir = TRAINING_DIR / scan_name
        if scan_dir.exists():
            response = send_from_directory(scan_dir, face_file)
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            return response
    
    return "Not found", 404

if __name__ == '__main__':
    print("🎲 RCubed Label Reviewer")
    print("=" * 50)
    
    scans = get_scan_list()
    confirmed_count = sum(1 for s in scans if s['confirmed'])
    print(f"📸 Total scans: {len(scans)}")
    print(f"✓  Confirmed: {confirmed_count}")
    print(f"⏳ Remaining: {len(scans) - confirmed_count}")
    print(f"🌐 Open: http://localhost:5000")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
