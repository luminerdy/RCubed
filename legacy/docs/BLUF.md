# RCubed — AI-Powered Rubik's Cube Solving Robot

## The Pitch

A Raspberry Pi 5 with a camera, four robotic arms, and an AI brain that can **scan, analyze, and solve a Rubik's Cube completely on its own** — no human input required.

## What Makes It Special

This isn't just a cube solver. It's a fully autonomous robotics pipeline built from scratch:

- 🎲 **Scans all 6 faces** using a choreographed servo sequence that rotates the cube in front of a camera — no face left unseen
- 🧠 **Reads colors using AI vision** — sends cropped face images to a vision model that identifies all 54 stickers
- 🧮 **Solves in under a second** — generates an optimal ~20-move solution using the Kociemba algorithm
- 🤖 **Physically executes the solution** — translates abstract moves like "R2 U' F B2" into precise servo choreography, including whole-cube rotations for faces without direct gripper access
- 🔧 **One command to rule them all** — `python3 auto_solve.py` runs the entire pipeline autonomously

## The Build

Based on the open-source OTVINTA RCR3D mechanical design (rcr3d.com) — a fully 3D-printed robot with 4 gripper arms, rack-and-pinion approach mechanisms, and 8 servo motors. The original design relied on a paid, closed-source Windows app. **We replaced it entirely** with a custom Python stack running natively on a Raspberry Pi 5.

## By The Numbers

| | |
|---|---|
| **Servos** | 8 (4× DS3218 grippers + 4× HS-311 rack-and-pinion) |
| **Printed Parts** | 50+ pieces, ~60 hours of print time |
| **Solution Length** | ~19-21 moves (near-optimal) |
| **Brain** | Raspberry Pi 5 + Hailo-8 AI accelerator |
| **Vision** | Claude AI via API (OpenCV fallback in development) |
| **Software** | 100% Python — OpenCV, Kociemba, custom servo control |

## Status

The software pipeline is **fully functional** — scan, read, solve, and execute all work. Currently hardening the mechanical grip to handle a complete 20-move solve without the cube slipping. We're one hardware tweak away from a fully autonomous solve.

## Built By

**Scotty** (hardware design, 3D printing, mechanical assembly, servo calibration) and **RubikPi** 🎲 (software, vision pipeline, move execution, AI integration) — a human-AI team building robots together.
