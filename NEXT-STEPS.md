# RCubed Next Steps

## Tomorrow - Lighting Test & More Collection

### 1. Test Different Lighting
**Goal:** See if 4000K neutral white improves Orange/Yellow distinction

**Current:** 6500K (daylight) + blue LEDs
**Try:** 4000K neutral white

**Test procedure:**
1. Load cube with `python3 load_cube.py`
2. Switch lamp to 4000K
3. Run single test scan: `python3 scan_6faces.py`
4. Check images: Are Orange/Yellow easier to distinguish?
5. If better: Use 4000K for all future training scans
6. If not: Stick with 6500K (consistency matters most!)

### 2. Continue Training Data Collection
**Current:** 8 scans labeled and validated
**Goal:** 50-100 total scans

**Process:**
```bash
cd ~/rcubed
python3 load_cube.py
# Insert scrambled cube
python3 collect_training_data.py
# Enter number of scans to collect
# Walk away, let it run!
```

**Then label in browser:**
- http://localhost:5000
- Hover + keyboard (1-6) to fix colors
- Confirm validates automatically
- All scans get Kociemba check

### 3. Export Training Dataset
**When:** After collecting 50-100 scans and labeling all

```bash
cd ~/rcubed/cube_labeler
python3 export_dataset.py
```

Creates YOLO format dataset in `~/rcubed/training_data/`

### 4. Train YOLOv8 Model
**When:** After export

```bash
pip3 install ultralytics
yolo train model=yolov8n.pt data=~/rcubed/training_data/data.yaml epochs=50 imgsz=280
```

### 5. Convert to Hailo Format
**When:** After training

Use Hailo Dataflow Compiler to convert trained model for AI hat.

### 6. Integrate Trained Model
**When:** Model is ready

Update `solve_cube.py` to use trained model instead of AI API.

---

## Key Files & Locations

**Collection:**
- `~/rcubed/collect_training_data.py` - Automated collection loop
- `~/rcubed/training_scans/` - Raw training images
- `~/rcubed/load_cube.py` - Prepare for collection

**Labeling:**
- http://localhost:5000 - Web labeler
- `~/rcubed/cube_labeler/data/labels/` - Label JSON files
- `~/rcubed/cube_labeler/validate_scan.py` - CLI validation

**Training:**
- `~/rcubed/cube_labeler/export_dataset.py` - Export to YOLO format
- `~/rcubed/training_data/` - Exported dataset (created by export script)

**Documentation:**
- `~/rcubed/TRAINING-COLLECTION-README.md` - Collection guide
- `~/rcubed/PROJECT-RCUBED.md` - Full project documentation
- `~/.openclaw/workspace/MEMORY.md` - Long-term memory
- `~/.openclaw/workspace/memory/2026-03-08.md` - Today's notes

---

## Remember

✅ **Consistency is key** - Use same lighting for ALL training scans
✅ **Variety matters** - Different scrambled states for better training
✅ **Validate early** - Check scans in labeler right away
✅ **Test incrementally** - Don't wait for 100 scans to test export/train

**Current status:** 8/50 scans collected (16% of minimum goal)

Good work today! 🎲
