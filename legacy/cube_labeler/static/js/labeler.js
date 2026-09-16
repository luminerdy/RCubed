// RCubed Label Reviewer - Frontend Logic
// Updated to work with scan_NNN directory structure and first_pass_labels.json

let scans = [];
let currentScanIndex = 0;
let currentLabels = null;
let selectedSticker = null;
let hoveredSticker = null;

// Color mapping for keyboard shortcuts
const KEY_TO_COLOR = {
    '1': 'W', '2': 'Y', '3': 'R', '4': 'O', '5': 'B', '6': 'G',
    'w': 'W', 'y': 'Y', 'r': 'R', 'o': 'O', 'b': 'B', 'g': 'G'
};

// Color cycling order for click-to-cycle
const COLOR_CYCLE = ['W', 'Y', 'R', 'O', 'B', 'G'];

// Initialize application
async function init() {
    try {
        const response = await fetch('/api/scans');
        const data = await response.json();
        scans = data.scans;
        
        document.getElementById('total-scans').textContent = scans.length;
        
        // Update header with confirmation stats
        updateProgressHeader(data);
        
        if (scans.length === 0) {
            alert('No scans found in training_scans/');
            return;
        }
        
        // Start with first unconfirmed scan, or first scan
        const firstUnconfirmed = scans.findIndex(s => !s.confirmed);
        const startIndex = firstUnconfirmed >= 0 ? firstUnconfirmed : 0;
        
        await loadScan(startIndex);
        setupEventListeners();
    } catch (error) {
        console.error('Failed to load scans:', error);
        alert('Error loading scans. Check console.');
    }
}

function updateProgressHeader(data) {
    // Update progress bar text
    const progressText = document.querySelector('.progress-text');
    if (progressText && data.confirmed !== undefined) {
        progressText.innerHTML = `
            Scan <span id="current-scan">0</span> / <span id="total-scans">${data.total}</span>
            &nbsp;|&nbsp; ✓ ${data.confirmed} confirmed, ${data.remaining} remaining
        `;
    }
}

// Load a scan and its labels
async function loadScan(index) {
    if (index < 0 || index >= scans.length) return;
    
    currentScanIndex = index;
    const scan = scans[index];
    const scanId = scan.id;
    
    // Update progress
    document.getElementById('current-scan').textContent = index + 1;
    const progress = ((index + 1) / scans.length) * 100;
    document.getElementById('progress').value = progress;
    
    // Load scan data
    const response = await fetch(`/api/scan/${scanId}`);
    currentLabels = await response.json();
    currentLabels.scan_id = scanId;
    
    // Update confirmed status display
    updateConfirmedStatus(scan.confirmed || currentLabels.verified);
    
    renderScan();
    updateColorCounts();
}

function updateConfirmedStatus(isConfirmed) {
    const confirmBtn = document.getElementById('confirm-btn');
    if (isConfirmed) {
        confirmBtn.classList.add('confirmed');
        confirmBtn.textContent = '✓ Confirmed';
    } else {
        confirmBtn.classList.remove('confirmed');
        confirmBtn.textContent = '✓ Confirm & Next';
    }
}

// Render all 6 faces
function renderScan() {
    const faceNames = ['front', 'back', 'right', 'left', 'top', 'bottom'];
    const scanName = `scan_${String(currentLabels.scan_id).padStart(3, '0')}`;
    const cacheBust = Date.now();
    
    faceNames.forEach(faceName => {
        const faceData = currentLabels.faces[faceName];
        
        // Set image - now using scan_NNN/face_N_name.jpg path
        const img = document.querySelector(`img[data-face="${faceName}"]`);
        const random = Math.random().toString(36).substring(7);
        img.src = `/images/${scanName}/${faceData.image}?v=${cacheBust}&r=${random}`;
        
        // Render sticker grid
        const gridEl = document.querySelector(`.sticker-grid[data-face="${faceName}"]`);
        gridEl.innerHTML = '';
        
        faceData.grid.forEach((row, r) => {
            row.forEach((color, c) => {
                const sticker = document.createElement('div');
                sticker.className = 'sticker';
                sticker.dataset.color = color;
                sticker.dataset.face = faceName;
                sticker.dataset.row = r;
                sticker.dataset.col = c;
                sticker.textContent = color;
                
                sticker.addEventListener('click', () => cycleStickerColor(faceName, r, c));
                sticker.addEventListener('mouseenter', () => hoverSticker(faceName, r, c));
                sticker.addEventListener('mouseleave', () => unhoverSticker());
                
                gridEl.appendChild(sticker);
            });
        });
    });
}

// Update color counter and validate
function updateColorCounts() {
    recalculateCounts();
    
    const counts = currentLabels.color_counts;
    const total = Object.values(counts).reduce((sum, n) => sum + n, 0);
    
    // Update individual counts
    ['W', 'Y', 'R', 'O', 'B', 'G'].forEach(color => {
        const count = counts[color] || 0;
        const el = document.getElementById(`count-${color}`);
        el.textContent = count;
        
        // Mark as valid/invalid
        const item = el.closest('.count-item');
        item.classList.toggle('valid', count === 9);
        item.classList.toggle('invalid', count !== 9);
    });
    
    // Update total
    document.getElementById('total-count').textContent = total;
    
    // Enable confirm button (always enabled for training data)
    document.getElementById('confirm-btn').disabled = false;
}

// Recalculate color counts from current labels
function recalculateCounts() {
    const counts = {};
    
    const faceNames = ['front', 'back', 'right', 'left', 'top', 'bottom'];
    faceNames.forEach(faceName => {
        const grid = currentLabels.faces[faceName].grid;
        grid.forEach(row => {
            row.forEach(color => {
                counts[color] = (counts[color] || 0) + 1;
            });
        });
    });
    
    currentLabels.color_counts = counts;
}

// Track hovered sticker for keyboard shortcuts
function hoverSticker(face, row, col) {
    hoveredSticker = {face, row, col};
    // Visual feedback
    const sticker = document.querySelector(
        `.sticker[data-face="${face}"][data-row="${row}"][data-col="${col}"]`
    );
    sticker.classList.add('hovered');
}

function unhoverSticker() {
    if (hoveredSticker) {
        const sticker = document.querySelector(
            `.sticker[data-face="${hoveredSticker.face}"][data-row="${hoveredSticker.row}"][data-col="${hoveredSticker.col}"]`
        );
        if (sticker) sticker.classList.remove('hovered');
    }
    hoveredSticker = null;
}

// Cycle sticker color on click
function cycleStickerColor(face, row, col) {
    const currentColor = currentLabels.faces[face].grid[row][col];
    const currentIndex = COLOR_CYCLE.indexOf(currentColor);
    const nextIndex = (currentIndex + 1) % COLOR_CYCLE.length;
    const nextColor = COLOR_CYCLE[nextIndex];
    
    setStickerColor(face, row, col, nextColor);
}

// Set sticker to specific color
function setStickerColor(face, row, col, color) {
    // Update labels
    currentLabels.faces[face].grid[row][col] = color;
    
    // Update UI
    const sticker = document.querySelector(
        `.sticker[data-face="${face}"][data-row="${row}"][data-col="${col}"]`
    );
    sticker.dataset.color = color;
    sticker.textContent = color;
    
    // Recalculate counts
    updateColorCounts();
}

// Close color picker
function closePicker() {
    document.getElementById('color-picker').classList.add('hidden');
    document.querySelectorAll('.sticker').forEach(el => {
        el.classList.remove('selected');
    });
    selectedSticker = null;
}

// Save and move to next
async function confirmAndNext() {
    const confirmBtn = document.getElementById('confirm-btn');
    confirmBtn.disabled = true;
    confirmBtn.textContent = 'Saving...';
    
    try {
        // Validate first
        const validateResp = await fetch('/api/validate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({faces: currentLabels.faces})
        });
        
        const validation = await validateResp.json();
        
        // Check for issues
        if (validation.errors && validation.errors.length > 0) {
            const proceed = confirm(
                `⚠️ Validation warnings:\n\n` +
                validation.errors.join('\n') + 
                `\n\nFor training data, this is often OK.\nSave anyway?`
            );
            if (!proceed) {
                confirmBtn.disabled = false;
                confirmBtn.textContent = '✓ Confirm & Next';
                return;
            }
        }
        
        // Save labels
        await fetch('/api/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(currentLabels)
        });
        
        // Mark current scan as confirmed locally
        scans[currentScanIndex].confirmed = true;
        
        // Find next unconfirmed scan
        let nextIndex = currentScanIndex + 1;
        while (nextIndex < scans.length && scans[nextIndex].confirmed) {
            nextIndex++;
        }
        
        if (nextIndex < scans.length) {
            await loadScan(nextIndex);
        } else if (currentScanIndex < scans.length - 1) {
            await loadScan(currentScanIndex + 1);
        } else {
            alert('🎉 All scans reviewed! Ready for YOLO export.');
            confirmBtn.textContent = '✓ All Done!';
            return;
        }
        
        confirmBtn.disabled = false;
        confirmBtn.textContent = '✓ Confirm & Next';
        
    } catch (error) {
        console.error('Save failed:', error);
        alert('Error: ' + error.message);
        confirmBtn.disabled = false;
        confirmBtn.textContent = '✓ Confirm & Next';
    }
}

// Delete current scan
async function deleteScan() {
    const scan = scans[currentScanIndex];
    const scanName = `scan_${String(scan.id).padStart(3, '0')}`;
    
    if (!confirm(`🗑️ Delete ${scanName}?\n\nThis will remove all images and labels for this scan. This cannot be undone.`)) {
        return;
    }
    
    try {
        await fetch('/api/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({scan_id: scan.id})
        });
        
        // Remove from local array
        scans.splice(currentScanIndex, 1);
        
        // Update totals
        document.getElementById('total-scans').textContent = scans.length;
        
        // Load next scan (or previous if at end)
        if (scans.length === 0) {
            alert('No scans remaining!');
            return;
        }
        
        const nextIndex = Math.min(currentScanIndex, scans.length - 1);
        await loadScan(nextIndex);
        
    } catch (error) {
        console.error('Delete failed:', error);
        alert('Error deleting scan: ' + error.message);
    }
}

// Jump to next unconfirmed scan
function jumpToNextUnconfirmed() {
    const nextUnconfirmed = scans.findIndex((s, i) => i > currentScanIndex && !s.confirmed);
    if (nextUnconfirmed >= 0) {
        loadScan(nextUnconfirmed);
    } else {
        // Wrap around
        const firstUnconfirmed = scans.findIndex(s => !s.confirmed);
        if (firstUnconfirmed >= 0) {
            loadScan(firstUnconfirmed);
        } else {
            alert('All scans confirmed! 🎉');
        }
    }
}

// Event listeners
function setupEventListeners() {
    // Navigation
    document.getElementById('prev-btn').addEventListener('click', () => {
        if (currentScanIndex > 0) {
            loadScan(currentScanIndex - 1);
        }
    });
    
    document.getElementById('next-btn').addEventListener('click', () => {
        if (currentScanIndex < scans.length - 1) {
            loadScan(currentScanIndex + 1);
        }
    });
    
    document.getElementById('confirm-btn').addEventListener('click', confirmAndNext);
    
    // Color picker buttons
    document.querySelectorAll('.color-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (selectedSticker) {
                setStickerColor(selectedSticker.face, selectedSticker.row, selectedSticker.col, btn.dataset.color);
                closePicker();
            }
        });
    });
    
    document.getElementById('cancel-btn').addEventListener('click', closePicker);
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Close picker with Escape
        if (e.key === 'Escape') {
            closePicker();
            return;
        }
        
        // Navigation with [ and ]
        if (e.key === '[' || (e.key === 'ArrowLeft' && !selectedSticker)) {
            if (currentScanIndex > 0) {
                loadScan(currentScanIndex - 1);
            }
            return;
        }
        
        if (e.key === ']' || (e.key === 'ArrowRight' && !selectedSticker)) {
            if (currentScanIndex < scans.length - 1) {
                loadScan(currentScanIndex + 1);
            }
            return;
        }
        
        // Jump to next unconfirmed with 'n'
        if (e.key === 'n' || e.key === 'N') {
            jumpToNextUnconfirmed();
            return;
        }
        
        // Delete with 'd' (requires shift for safety)
        if (e.key === 'D' && e.shiftKey) {
            deleteScan();
            return;
        }
        
        // Confirm with Enter
        if (e.key === 'Enter' && !selectedSticker) {
            const confirmBtn = document.getElementById('confirm-btn');
            if (!confirmBtn.disabled) {
                confirmAndNext();
            }
            return;
        }
        
        // Color selection (1-6 or w/y/r/o/b/g) - works on hovered sticker
        if (KEY_TO_COLOR[e.key]) {
            const target = hoveredSticker || selectedSticker;
            if (target) {
                setStickerColor(target.face, target.row, target.col, KEY_TO_COLOR[e.key]);
                if (selectedSticker) {
                    closePicker();
                }
            }
        }
    });
    
    // Click outside modal to close
    document.getElementById('color-picker').addEventListener('click', (e) => {
        if (e.target.id === 'color-picker') {
            closePicker();
        }
    });
}

// Start application
init();
