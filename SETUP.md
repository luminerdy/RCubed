# RCubed - Pi Setup Guide

Fresh Raspberry Pi OS setup for running the RCubed cube-solving robot.

## Requirements

- Raspberry Pi 5 (16GB recommended)
- Raspberry Pi OS Bookworm (64-bit)
- Pololu Maestro servo controller (USB)
- USB camera

---

## Step 1: Serial Port Access

Add your user to the `dialout` group so Python can talk to the Maestro over USB serial:

```bash
sudo usermod -a -G dialout $USER
```

Then **log out and back in** (or reboot). Verify with:

```bash
groups $USER   # should include "dialout"
```

> **Note:** On a fresh Pi OS install this is required even if you were in the group before — it doesn't carry over from a reflash.

---

## Step 2: Clone the Repo

```bash
cd ~
git clone https://github.com/luminerdy/RCubed rcubed
```

---

## Step 3: Install Python Dependencies

Pi OS Bookworm restricts system pip — use `--break-system-packages`:

```bash
pip3 install --break-system-packages pyserial opencv-python kociemba anthropic flask numpy
```

Verify everything installed cleanly:

```bash
cd ~/rcubed
python3 -c "import serial, cv2, kociemba, anthropic, flask, numpy; print('All imports OK')"
```

---

## Step 4: Pololu Maestro Configuration

The Maestro must be set to **USB Dual Port** serial mode (this is stored on the device itself, not the Pi).

- If the Maestro was already configured before the reflash: plug it in and it should just work.
- If it's a fresh Maestro: use [Pololu's Maestro Control Center](https://www.pololu.com/docs/0J40) (Windows/Mac) to set the serial mode.

Verify the Maestro is detected after plugging in:

```bash
ls /dev/ttyACM*   # should show /dev/ttyACM0
```

> If it shows `ttyACM1` instead of `ttyACM0` (can happen after USB replug), update the port in `config/servo_config.json` or pass it as an argument.

---

## Step 5: Anthropic API Key

`src/auto_solve.py` uses the Anthropic API for color detection until a local vision model is trained. Set your key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

To make it permanent, add that line to `~/.bashrc`.

---

## Step 6: Camera White Balance

Lock camera white balance to prevent color shift during scanning:

```bash
v4l2-ctl -c white_balance_automatic=0 -c white_balance_temperature=5500
```

This needs to be run each session before scanning (camera resets on reconnect).

---

## Step 7: Smoke Test

With the Maestro plugged in and servos powered:

```bash
cd ~/rcubed
python3 scripts/retract_all.py    # safely retracts all RP servos
python3 scripts/test_grippers.py  # cycles each gripper individually
```

---

## Quick Start (full solve)

```bash
cd ~/rcubed

# 1. Load the cube
python3 scripts/set_neutral.py

# 2. Scan all 6 faces
python3 src/scan_v7.py

# 3. Execute a solution
python3 src/cube_controller.py "R U R' F2"
```

---

## Directory Reference

```
rcubed/
├── src/                    # Main application code
│   ├── cube_controller.py  # Robot control (standard cube notation)
│   ├── scan_v7.py          # 6-face scanning sequence
│   ├── solve_cube.py       # Kociemba solver integration
│   ├── auto_solve.py       # Full autonomous pipeline (needs API key)
│   ├── collect_training_v2.py
│   └── maestro.py          # Pololu Maestro serial library
├── scripts/                # Utility scripts
│   ├── retract_all.py      # Safety: retract all RP servos
│   ├── set_neutral.py      # Reset all servos to neutral
│   ├── test_grippers.py    # Test each gripper
│   ├── servo_calibrate.py  # Interactive calibration
│   ├── calibrate_timing.py # Measure actual servo timing
│   └── camera_adjust.py    # Camera setup helper
├── cube_labeler/           # Flask web app for labeling training data
├── config/
│   └── servo_config.json   # Servo calibration values
└── docs/                   # Documentation
```

---

## Troubleshooting

**Maestro unresponsive / USB errors during execution**
Reboot the Pi or power-cycle the Maestro. This is a known intermittent USB communication issue, not a hardware failure.

**`/dev/ttyACM0` not found**
Check that the Maestro is plugged in and in USB Dual Port mode. Try `dmesg | tail -20` after plugging in to see if the OS detected it.

**Permission denied on `/dev/ttyACM0`**
User isn't in the `dialout` group yet — run Step 1 and log out/in.

**Color detection wrong (W/Y confusion)**
Blue LED lighting causes this. Use manual verification or switch to a white LED for scanning.
