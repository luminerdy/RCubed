# RCubed - Pi Setup Guide

Fresh Raspberry Pi OS setup for running the RCubed cube-solving robot.

## Requirements

- Raspberry Pi 5 (16GB recommended)
- Raspberry Pi OS Bookworm (64-bit)
- Pololu Maestro servo controller (USB)
- USB camera

---

## Step 0: Hardware, Wiring & Power

> ⚠️ **This section is a stub — fill in the electrical details.** Everything
> below the software steps can be recovered by reading the code; this cannot.
> If the robot ever has to be rebuilt or rewired, this is the only record.

The mechanical build is the [RCR3D design by O.T. Vinta](https://rcr3d.com) —
4 gripper arms, ~50 printed parts. Refer to their assembly docs for the frame.

### Servo channel map (verified)

| Channel | Servo | Function |
|---------|-------|----------|
| 0 | DS3218 | Left gripper — rotates Orange face |
| 1 | DS3218 | Left rack-and-pinion — approach/retract |
| 2 | DS3218 | Up gripper — rotates Blue face |
| 3 | DS3218 | Up rack-and-pinion |
| 6 | DS3218 | Right gripper — rotates Red face |
| 7 | DS3218 | Right rack-and-pinion |
| 8 | DS3218 | Down gripper — rotates Green face |
| 9 | DS3218 | Down rack-and-pinion |

Channels 4, 5, 10, 11 are unused. Even = gripper, odd = rack-and-pinion.

### Power — TODO

DS3218 servos stall around 2.5 A each, so eight of them cannot run off the Pi or
off Maestro USB power. Record the actual build:

- [ ] Servo supply: make/model, voltage, current rating
- [ ] How servo power reaches the Maestro's servo power rail (barrel jack? screw terminal?)
- [ ] State of the Maestro's **VSRV=VIN power jumper** — must be *cut/removed* when
      supplying servo power separately, or the supply back-feeds USB
- [ ] Common ground between servo supply and Maestro
- [ ] Pi 5 supply (needs the 27 W USB-C PD unit if the Hailo-8 hat is fitted)
- [ ] Power-on order, if it matters (servo supply before/after Pi?)

### Lighting — TODO

The scan rig currently uses a **blue LED**, which is the known cause of the
white/yellow confusion in color detection. Record:

- [ ] LED type, mounting, and power source
- [ ] Whether it has been swapped to white (this is a listed fix — see Troubleshooting)

### Camera — TODO

- [ ] Camera model (currently a SunplusIT USB webcam, `4bcf:4c10`)
- [ ] Mount position and how the face-crop bounds were derived
      (`CUBE_BOUNDS` in `src/auto_solve.py`: x 180-460, y 75-400)

### Hailo-8

The Pi 5 has a Hailo-8 AI hat fitted, but **nothing in this project uses it yet**.
No Hailo runtime or driver setup is required to run the robot today — vision goes
through the Anthropic API. See `docs/ACTION-PLAN.md` Phase 5 for the plan to
deploy a local model onto it.

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
cd ~/rcubed
pip3 install --break-system-packages -r requirements.txt
```

> Don't install `cube_labeler/requirements.txt` separately — it just points back
> at the root file. Installing an older pinned set there will downgrade OpenCV
> and NumPy out from under the rest of the project.

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
ls -l /dev/serial/by-id/
```

You should see two entries for the Maestro:

```
usb-Pololu_Corporation_..._USB_Servo_Controller_00490905-if00 -> ../../ttyACM0
usb-Pololu_Corporation_..._USB_Servo_Controller_00490905-if02 -> ../../ttyACM1
```

**`-if00` is the Command Port** — that's the one the code talks to. `-if02` is
the TTL Serial Port; sending servo commands there does nothing.

The `ttyACM*` numbers are assigned in USB enumeration order and shift when other
serial devices are attached, so nothing hardcodes them. `maestro.find_port()`
resolves the command port via the stable `by-id` name, and every script uses it
automatically. To override (multiple Maestros, unusual setup), the scripts that
take a port accept `--port`:

```bash
python3 src/cube_controller.py --port /dev/ttyACM2 "R U R'"
```

> **Historical note:** older versions of these scripts fell back to `/dev/ttyACM1`
> when `ttyACM0` failed to open. That was wrong — it lands on the TTL port and
> the robot silently does nothing. If you see that pattern anywhere, it's stale.

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
sudo apt install -y v4l-utils   # preinstalled on Pi OS Desktop, missing on Lite
v4l2-ctl -c white_balance_automatic=0 -c white_balance_temperature=5500
```

This needs to be run each session before scanning (camera resets on reconnect).

Confirm which `/dev/video*` node is the webcam first — a Pi 5 exposes a lot of
ISP nodes alongside it, and the code assumes index 0:

```bash
v4l2-ctl --list-devices
python3 scripts/camera_test.py    # writes a test capture from index 0
```

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

## Training Data (not in git)

The labeled scans are **not** recoverable from a clone — `training_scans/` is
gitignored because the images are too large. A fresh Pi gets the *labels* but not
the *pixels*, so `cube_labeler/export_dataset.py` will refuse to run until images
are restored.

There are two label sets, in two different layouts:

| Scans | Images | Labels | Read by |
|-------|--------|--------|---------|
| 001-008 | `cube_labeler/data/images/*.jpg` (flat) | `cube_labeler/data/labels/scan_N.json` | `export_dataset.py` |
| 009+ | `training_scans/scan_NNN/face_N_*.jpg` | `first_pass_labels.json` | `cube_labeler/app.py` |

`export_dataset.py` currently only understands the first set. Unifying the two is
outstanding work — see `docs/ACTION-PLAN.md` Phase 4.

To restore or rebuild:

```bash
# Option A: copy training_scans/ and cube_labeler/data/images/ from a backup

# Option B: collect fresh scans (robot must be assembled and calibrated)
python3 src/collect_training_v2.py
python3 cube_labeler/app.py     # label them at http://localhost:5000
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
│   └── servo_config.json   # Servo calibration values (no port setting — see Step 4)
├── requirements.txt        # Python dependencies
└── docs/                   # Documentation
```

---

## Troubleshooting

**Maestro unresponsive / USB errors during execution**
Reboot the Pi or power-cycle the Maestro. This is a known intermittent USB communication issue, not a hardware failure.

**Maestro not found**
Check `ls -l /dev/serial/by-id/` for a `Pololu...-if00` entry. If nothing is
there, confirm the Maestro is plugged in and in USB Dual Port mode, then try
`dmesg | tail -20` to see whether the OS enumerated it at all.

**Permission denied opening the serial port**
User isn't in the `dialout` group yet — run Step 1 and log out/in.

**Scripts connect but the servos never move**
You're probably on the TTL port (`-if02`) instead of the command port (`-if00`).
Don't pass `--port /dev/ttyACM1` by hand; let `maestro.find_port()` resolve it.
Also confirm the servo power supply is on — the Maestro enumerates over USB with
no servo power at all, so a connection succeeding proves nothing about power.

**Color detection wrong (W/Y confusion)**
Blue LED lighting causes this. Use manual verification or switch to a white LED for scanning.
