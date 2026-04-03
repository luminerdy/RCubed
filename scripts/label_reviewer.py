#!/usr/bin/env python3
"""
Label Reviewer - Review and confirm first-pass labels for Rubik's cube training data.
Run: python3 label_reviewer.py
Then open: http://localhost:5001
"""

from flask import Flask, render_template_string, jsonify, request, send_from_directory
import json
import os
from pathlib import Path

app = Flask(__name__)

SCANS_DIR = Path("/home/luminerdy/rcubed/training_scans")
LABELS_FILE = Path("/home/luminerdy/rcubed/first_pass_labels.json")
CONFIRMED_FILE = Path("/home/luminerdy/rcubed/confirmed_labels.json")

# Color display mapping
COLOR_MAP = {
    'W': ('#FFFFFF', 'White'),
    'Y': ('#FFFF00', 'Yellow'),
    'R': ('#FF0000', 'Red'),
    'O': ('#FFA500', 'Orange'),
    'B': ('#0000FF', 'Blue'),
    'G': ('#00FF00', 'Green'),
}

def load_labels():
    if LABELS_FILE.exists():
        with open(LABELS_FILE) as f:
            return json.load(f)
    return {}

def save_labels(labels):
    with open(LABELS_FILE, 'w') as f:
        json.dump(labels, f, indent=2)

def load_confirmed():
    if CONFIRMED_FILE.exists():
        with open(CONFIRMED_FILE) as f:
            return json.load(f)
    return {"confirmed": [], "reviewed_scans": []}

def save_confirmed(confirmed):
    with open(CONFIRMED_FILE, 'w') as f:
        json.dump(confirmed, f, indent=2)

def get_all_scans():
    """Get list of all scan directories that have labels."""
    labels = load_labels()
    scans = set()
    for key in labels:
        scan = key.split('/')[0]
        scans.add(scan)
    return sorted(scans)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Label Reviewer - RCubed</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e; 
            color: #eee; 
            margin: 0; 
            padding: 20px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #333;
        }
        h1 { margin: 0; color: #4fc3f7; }
        .stats {
            display: flex;
            gap: 20px;
            font-size: 14px;
        }
        .stat { 
            background: #2a2a4a; 
            padding: 8px 15px; 
            border-radius: 5px;
        }
        .stat-value { color: #4fc3f7; font-weight: bold; }
        
        .nav-controls {
            display: flex;
            gap: 10px;
            align-items: center;
            margin-bottom: 20px;
        }
        select, button {
            padding: 10px 15px;
            border: none;
            border-radius: 5px;
            font-size: 14px;
            cursor: pointer;
        }
        select { background: #2a2a4a; color: #eee; min-width: 150px; }
        button { background: #4fc3f7; color: #000; font-weight: bold; }
        button:hover { background: #81d4fa; }
        button.confirm-btn { background: #4caf50; }
        button.confirm-btn:hover { background: #66bb6a; }
        button.confirmed { background: #2e7d32; }
        button:disabled { background: #555; color: #888; cursor: not-allowed; }
        
        .filter-btns { display: flex; gap: 5px; }
        .filter-btns button { 
            padding: 8px 12px; 
            background: #2a2a4a;
            color: #eee;
        }
        .filter-btns button.active { background: #4fc3f7; color: #000; }
        
        .faces-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            max-width: 1400px;
        }
        .face-card {
            background: #2a2a4a;
            border-radius: 10px;
            padding: 15px;
            position: relative;
        }
        .face-card.confirmed { border: 2px solid #4caf50; }
        .face-title {
            font-size: 14px;
            color: #888;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
        }
        .face-image {
            width: 100%;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        
        .label-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 4px;
            margin-bottom: 10px;
        }
        .label-cell {
            aspect-ratio: 1;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 18px;
            cursor: pointer;
            border: 2px solid transparent;
            transition: all 0.15s;
        }
        .label-cell:hover { transform: scale(1.1); border-color: #fff; }
        .label-cell.selected { border-color: #4fc3f7; box-shadow: 0 0 10px #4fc3f7; }
        
        .color-picker {
            display: flex;
            gap: 5px;
            justify-content: center;
            margin-top: 10px;
        }
        .color-btn {
            width: 30px;
            height: 30px;
            border-radius: 50%;
            border: 2px solid #444;
            cursor: pointer;
            transition: all 0.15s;
        }
        .color-btn:hover { transform: scale(1.2); border-color: #fff; }
        
        .keyboard-hint {
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 20px;
        }
        kbd {
            background: #333;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
        }
        
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #4caf50;
            color: #fff;
            padding: 15px 25px;
            border-radius: 5px;
            display: none;
            animation: fadeIn 0.3s;
        }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎲 Label Reviewer</h1>
        <div class="stats">
            <div class="stat">Scans: <span class="stat-value" id="totalScans">0</span></div>
            <div class="stat">Confirmed: <span class="stat-value" id="confirmedScans">0</span></div>
            <div class="stat">Remaining: <span class="stat-value" id="remainingScans">0</span></div>
        </div>
    </div>
    
    <div class="nav-controls">
        <select id="scanSelect" onchange="loadScan(this.value)"></select>
        <button onclick="prevScan()">← Prev</button>
        <button onclick="nextScan()">Next →</button>
        <button onclick="nextUnconfirmed()">Next Unconfirmed</button>
        <button id="confirmScanBtn" class="confirm-btn" onclick="confirmScan()">✓ Confirm Scan</button>
        <div class="filter-btns">
            <button id="filterAll" class="active" onclick="setFilter('all')">All</button>
            <button id="filterUnconfirmed" onclick="setFilter('unconfirmed')">Unconfirmed</button>
            <button id="filterConfirmed" onclick="setFilter('confirmed')">Confirmed</button>
        </div>
    </div>
    
    <div class="faces-grid" id="facesGrid"></div>
    
    <div class="keyboard-hint">
        <kbd>1-6</kbd> Select face | <kbd>W</kbd><kbd>Y</kbd><kbd>R</kbd><kbd>O</kbd><kbd>B</kbd><kbd>G</kbd> Set color | 
        <kbd>←</kbd><kbd>→</kbd> Navigate cells | <kbd>Enter</kbd> Confirm scan | <kbd>[</kbd><kbd>]</kbd> Prev/Next scan
    </div>
    
    <div class="toast" id="toast"></div>

<script>
let allScans = [];
let confirmedScans = [];
let currentScan = null;
let labels = {};
let selectedCell = null;
let currentFilter = 'all';

const COLORS = {
    'W': '#FFFFFF', 'Y': '#FFFF00', 'R': '#FF0000',
    'O': '#FFA500', 'B': '#0000FF', 'G': '#00FF00'
};
const FACES = ['face_1_front', 'face_2_back', 'face_3_right', 'face_4_left', 'face_5_top', 'face_6_bottom'];

async function init() {
    const resp = await fetch('/api/scans');
    const data = await resp.json();
    allScans = data.scans;
    confirmedScans = data.confirmed;
    updateStats();
    populateScanSelect();
    if (allScans.length > 0) {
        loadScan(allScans[0]);
    }
}

function updateStats() {
    document.getElementById('totalScans').textContent = allScans.length;
    document.getElementById('confirmedScans').textContent = confirmedScans.length;
    document.getElementById('remainingScans').textContent = allScans.length - confirmedScans.length;
}

function populateScanSelect() {
    const select = document.getElementById('scanSelect');
    select.innerHTML = '';
    let filteredScans = allScans;
    if (currentFilter === 'confirmed') {
        filteredScans = allScans.filter(s => confirmedScans.includes(s));
    } else if (currentFilter === 'unconfirmed') {
        filteredScans = allScans.filter(s => !confirmedScans.includes(s));
    }
    filteredScans.forEach(scan => {
        const opt = document.createElement('option');
        opt.value = scan;
        opt.textContent = scan + (confirmedScans.includes(scan) ? ' ✓' : '');
        select.appendChild(opt);
    });
    if (currentScan) select.value = currentScan;
}

function setFilter(filter) {
    currentFilter = filter;
    document.querySelectorAll('.filter-btns button').forEach(b => b.classList.remove('active'));
    document.getElementById('filter' + filter.charAt(0).toUpperCase() + filter.slice(1)).classList.add('active');
    populateScanSelect();
}

async function loadScan(scanName) {
    currentScan = scanName;
    document.getElementById('scanSelect').value = scanName;
    
    const resp = await fetch(`/api/scan/${scanName}`);
    labels = await resp.json();
    
    const isConfirmed = confirmedScans.includes(scanName);
    const btn = document.getElementById('confirmScanBtn');
    btn.textContent = isConfirmed ? '✓ Confirmed' : '✓ Confirm Scan';
    btn.classList.toggle('confirmed', isConfirmed);
    
    renderFaces();
}

function renderFaces() {
    const grid = document.getElementById('facesGrid');
    grid.innerHTML = '';
    
    FACES.forEach((face, faceIdx) => {
        const key = `${currentScan}/${face}.jpg`;
        const faceLabels = labels[key] || Array(9).fill('W');
        const isConfirmed = confirmedScans.includes(currentScan);
        
        const card = document.createElement('div');
        card.className = 'face-card' + (isConfirmed ? ' confirmed' : '');
        card.innerHTML = `
            <div class="face-title">
                <span>${face.replace('face_', '').replace('_', ' - ')}</span>
                <span style="color: #4fc3f7">[${faceIdx + 1}]</span>
            </div>
            <img class="face-image" src="/image/${currentScan}/${face}.jpg" alt="${face}">
            <div class="label-grid" id="grid-${faceIdx}">
                ${faceLabels.map((c, i) => `
                    <div class="label-cell" 
                         style="background: ${COLORS[c]}; color: ${c === 'W' || c === 'Y' || c === 'G' ? '#000' : '#fff'}"
                         data-face="${faceIdx}" data-cell="${i}"
                         onclick="selectCell(${faceIdx}, ${i})">
                        ${c}
                    </div>
                `).join('')}
            </div>
            <div class="color-picker">
                ${Object.entries(COLORS).map(([c, hex]) => `
                    <div class="color-btn" style="background: ${hex}" onclick="setColor('${c}')" title="${c}"></div>
                `).join('')}
            </div>
        `;
        grid.appendChild(card);
    });
}

function selectCell(faceIdx, cellIdx) {
    document.querySelectorAll('.label-cell').forEach(c => c.classList.remove('selected'));
    const cell = document.querySelector(`[data-face="${faceIdx}"][data-cell="${cellIdx}"]`);
    cell.classList.add('selected');
    selectedCell = { face: faceIdx, cell: cellIdx };
}

async function setColor(color) {
    if (!selectedCell) return;
    
    const face = FACES[selectedCell.face];
    const key = `${currentScan}/${face}.jpg`;
    if (!labels[key]) labels[key] = Array(9).fill('W');
    labels[key][selectedCell.cell] = color;
    
    // Save immediately
    await fetch('/api/update', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ key, labels: labels[key] })
    });
    
    renderFaces();
    
    // Move to next cell
    if (selectedCell.cell < 8) {
        selectCell(selectedCell.face, selectedCell.cell + 1);
    } else if (selectedCell.face < 5) {
        selectCell(selectedCell.face + 1, 0);
    }
}

async function confirmScan() {
    const resp = await fetch('/api/confirm', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ scan: currentScan })
    });
    const data = await resp.json();
    confirmedScans = data.confirmed;
    updateStats();
    populateScanSelect();
    loadScan(currentScan);
    showToast('Scan confirmed! ✓');
}

function prevScan() {
    const select = document.getElementById('scanSelect');
    const opts = Array.from(select.options).map(o => o.value);
    const idx = opts.indexOf(currentScan);
    if (idx > 0) loadScan(opts[idx - 1]);
}

function nextScan() {
    const select = document.getElementById('scanSelect');
    const opts = Array.from(select.options).map(o => o.value);
    const idx = opts.indexOf(currentScan);
    if (idx < opts.length - 1) loadScan(opts[idx + 1]);
}

function nextUnconfirmed() {
    const unconfirmed = allScans.filter(s => !confirmedScans.includes(s));
    if (unconfirmed.length > 0) {
        loadScan(unconfirmed[0]);
    } else {
        showToast('All scans confirmed! 🎉');
    }
}

function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.style.display = 'block';
    setTimeout(() => toast.style.display = 'none', 2000);
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.key >= '1' && e.key <= '6') {
        selectCell(parseInt(e.key) - 1, 0);
    } else if ('wyrobg'.includes(e.key.toLowerCase())) {
        setColor(e.key.toUpperCase());
    } else if (e.key === 'ArrowRight' && selectedCell) {
        const next = selectedCell.cell < 8 ? selectedCell.cell + 1 : 0;
        selectCell(selectedCell.face, next);
    } else if (e.key === 'ArrowLeft' && selectedCell) {
        const prev = selectedCell.cell > 0 ? selectedCell.cell - 1 : 8;
        selectCell(selectedCell.face, prev);
    } else if (e.key === 'ArrowDown' && selectedCell) {
        const next = Math.min(selectedCell.cell + 3, 8);
        selectCell(selectedCell.face, next);
    } else if (e.key === 'ArrowUp' && selectedCell) {
        const prev = Math.max(selectedCell.cell - 3, 0);
        selectCell(selectedCell.face, prev);
    } else if (e.key === 'Enter') {
        confirmScan();
    } else if (e.key === '[') {
        prevScan();
    } else if (e.key === ']') {
        nextScan();
    }
});

init();
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/image/<scan>/<face>')
def serve_image(scan, face):
    return send_from_directory(SCANS_DIR / scan, face)

@app.route('/api/scans')
def api_scans():
    scans = get_all_scans()
    confirmed = load_confirmed()
    return jsonify({
        'scans': scans,
        'confirmed': confirmed.get('reviewed_scans', [])
    })

@app.route('/api/scan/<scan_name>')
def api_scan(scan_name):
    labels = load_labels()
    scan_labels = {k: v for k, v in labels.items() if k.startswith(scan_name + '/')}
    return jsonify(scan_labels)

@app.route('/api/update', methods=['POST'])
def api_update():
    data = request.json
    labels = load_labels()
    labels[data['key']] = data['labels']
    save_labels(labels)
    return jsonify({'ok': True})

@app.route('/api/confirm', methods=['POST'])
def api_confirm():
    data = request.json
    scan = data['scan']
    confirmed = load_confirmed()
    
    if scan not in confirmed['reviewed_scans']:
        confirmed['reviewed_scans'].append(scan)
        # Also track individual confirmed images
        labels = load_labels()
        for key in labels:
            if key.startswith(scan + '/') and key not in confirmed['confirmed']:
                confirmed['confirmed'].append(key)
        save_confirmed(confirmed)
    
    return jsonify({'confirmed': confirmed['reviewed_scans']})

if __name__ == '__main__':
    print("🎲 Label Reviewer starting...")
    print("   Open: http://localhost:5001")
    print("   Press Ctrl+C to stop")
    app.run(host='0.0.0.0', port=5001, debug=False)
