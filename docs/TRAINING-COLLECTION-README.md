# Automated Training Data Collection

## Quick Start

### 1. Load a Scrambled Cube

```bash
cd ~/rcubed
python3 load_cube.py
# Insert scrambled cube (White front, Blue top)
```

### 2. Run Collection Script

```bash
python3 collect_training_data.py
```

**Prompts:**
- "How many scans?" → Enter 50-100 (recommended)
- "Press Enter to start" → Press Enter

**What it does:**
1. ✅ Scans cube (6 cropped face images)
2. 📦 Saves to `training_scans/scan_NNN_face_N_name.jpg`
3. 🔀 Scrambles cube with 3-6 random moves
4. 🔄 Repeats until target count reached

**No manual intervention needed!** Just let it run.

### 3. Verify/Correct in Labeler

```bash
# Open http://localhost:5000 in browser
# (Flask app should already be running)
```

- Labeler automatically shows training scans
- Hover + press 1-6 to fix wrong colors
- Click Confirm when counts are valid (9 each)
- Navigate through all scans

### 4. Export Training Data

```bash
cd ~/rcubed/cube_labeler
python3 export_dataset.py
```

Creates `~/rcubed/training_data/` with YOLO format ready for training.

---

## Details

### File Structure

```
~/rcubed/
├── scans/                    # Regular scans (manual)
│   └── face_*.jpg
├── training_scans/           # Automated collection
│   ├── scan_001_face_1_front.jpg
│   ├── scan_001_face_2_back.jpg
│   └── ...
└── cube_labeler/
    └── data/
        └── labels/
            ├── scan_1.json   # Labels for training scan 1
            └── ...
```

### Scramble Algorithm

- Generates 3-6 random moves per iteration
- Moves: R, R', R2, L, L', L2, U, U', U2, D, D', D2, F, F', F2, B, B', B2
- Avoids consecutive same-face moves (e.g., R followed by R')
- Uses `move_executor_v2.py` with orientation tracking

### Why 50-100 Scans?

- **50 scans** = 300 images = minimum for decent model
- **100 scans** = 600 images = recommended for good accuracy
- **More diversity** = better model generalization

### What Gets Auto-Detected?

- OpenCV provides initial color guess (~60-70% accurate)
- You verify/correct in web labeler
- Common errors: W/Y confusion under blue LED
- Corrections saved to labels/scan_N.json

### Interrupting Collection

Press `Ctrl+C` to stop early. Collected scans are already saved.

---

## Tips

### Varied Scrambles

The script scrambles randomly, but you can also:
- Manually scramble between some iterations (when prompted)
- Start with different initial scrambles for more variety

### Lighting Consistency

Keep lighting the same across all collections:
- Same blue LED brightness
- Same time of day (if near windows)
- Consistent camera position

### Quality Check

After collection, spot-check a few scans in the labeler:
- Make sure colors are detectable
- Verify cropping looks good
- Check for any mechanical issues (cube slipping, etc.)

### Batch Labeling

**Efficient workflow:**
1. Collect all 50-100 scans first (don't label yet)
2. Then label all at once in web UI
3. Export when all verified
4. Train model

**Why?** Labeling in batches is faster than switching contexts.

---

## Troubleshooting

**"Scan failed!"**
- Check camera connection
- Verify Maestro is responding
- Try rebooting if Maestro is stuck

**"Scramble failed!"**
- Check servo communication
- May need to power cycle Maestro
- Cube might have bound during previous move

**Wrong directory?**
- Images save to `training_scans/` (not `scans/`)
- Labeler automatically finds both

**Labeler not showing new scans?**
- Refresh browser
- Check `training_scans/` folder exists and has images

---

## Next Steps After Collection

1. **Label all scans** in web UI (http://localhost:5000)
2. **Export dataset:** `cd cube_labeler && python3 export_dataset.py`
3. **Train YOLOv8:**
   ```bash
   pip3 install ultralytics
   yolo train model=yolov8n.pt data=~/rcubed/training_data/data.yaml epochs=50
   ```
4. **Convert to Hailo** format for AI hat
5. **Replace OpenCV** detection with trained model in `solve_cube.py`

---

Built for RCubed by RubikPi 🎲
