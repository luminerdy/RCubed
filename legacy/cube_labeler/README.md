# RCubed Sticker Labeler

Web application for labeling Rubik's cube face images to create training data for local color detection model.

## Quick Start

### 1. Install Dependencies

```bash
cd ~/rcubed/cube_labeler
pip3 install -r requirements.txt
```

### 2. Run Application

```bash
python3 app.py
```

Then open browser: **http://localhost:5000**

## Usage Workflow

### Phase 1: Scan Cubes

```bash
# For each scramble:
cd ~/rcubed
python3 load_cube.py          # Set load position
# Insert cube (White front, Blue top)
python3 scan_6faces.py        # Capture all 6 faces
```

### Phase 2: Label Stickers

1. **Open labeler:** http://localhost:5000
2. **Review auto-detected colors** (OpenCV initial guess)
3. **Click any incorrect sticker** → pick correct color (1-6 keys)
4. **Watch color counter** (should show 9 of each color)
5. **Confirm button** enables when counts are valid
6. **Press Confirm** (or Enter) to save and move to next scan
7. **Repeat** for all scans

### Phase 3: Export Training Data

```bash
cd ~/rcubed/cube_labeler
python3 export_dataset.py
```

Creates `~/rcubed/training_data/` with YOLO format ready for training.

## Keyboard Shortcuts

- **← →** Navigate between scans
- **Click sticker** Select for editing
- **1** = White
- **2** = Yellow
- **3** = Red
- **4** = Orange
- **5** = Blue
- **6** = Green
- **Enter** Confirm & next (when valid)
- **Esc** Cancel selection

## Color Counter

At the top of the screen, you'll see a real-time count of each color across all 6 faces:

- **Green count (9)** = Valid ✓
- **Red count (≠9)** = Invalid ✗

**Confirm button** only enables when ALL colors = 9 (total 54 stickers).

## Calibration Mode (Optional)

For best detection accuracy:

1. **Scan a solved cube** first
2. Labeler will prompt for calibration
3. Tell it which face is which color
4. System learns color references under your blue LED lighting
5. Future detections will be more accurate

## Data Format

Labels saved to `data/labels/scan_N.json`:

```json
{
  "scan_id": 0,
  "faces": {
    "front": {
      "image": "face_1_front.jpg",
      "grid": [
        ["G","R","Y"],
        ["G","W","W"],
        ["W","B","B"]
      ]
    },
    // ... 5 more faces
  },
  "verified": true,
  "color_counts": {"W": 9, "Y": 9, "R": 9, "O": 9, "B": 9, "G": 9}
}
```

## Training YOLOv8

After exporting:

```bash
# Install ultralytics
pip3 install ultralytics

# Train YOLOv8-nano
yolo train model=yolov8n.pt data=~/rcubed/training_data/data.yaml epochs=50 imgsz=640

# Best model saved to: runs/detect/train/weights/best.pt
```

## Converting to Hailo

```bash
# Use Hailo Dataflow Compiler to convert YOLOv8 → Hailo format
# Then run on Hailo-8 AI hat for fast local inference
```

## Tips

- **Label 50-100 scans** for good training data (300-600 images)
- **Vary scrambles** - don't just repeat same patterns
- **Double-check W/Y** - most common confusion under blue LED
- **Save often** - app auto-saves on confirm
- **Use keyboard** - much faster than mouse clicking

## Troubleshooting

**No scans found:**
- Check `data/images/` symlink points to `~/rcubed/scans/`
- Run scan_6faces.py first

**Colors way off:**
- Run calibration with solved cube
- Or manually edit `data/config.json` color references

**Confirm button disabled:**
- Check color counter - must be exactly 9 of each
- Verify no typos in sticker labels

---

Built for RCubed by RubikPi 🎲
