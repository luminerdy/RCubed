#!/usr/bin/env python3
"""
RCubed Cube Controller - Modular Hardware Abstraction
======================================================

Clean, stateful controller for the RCubed robot. Tracks gripper positions
and cube orientation automatically. Every operation is safe and idempotent.

Design Philosophy:
- Track ALL state internally (gripper positions, RP status, cube orientation)
- Every rotation function handles its own prep (no manual "setup" calls)
- Operations are composable: rotate_left_90() just works
- No need to know which grippers are where - the controller handles it

Usage:
    from cube_controller import CubeController
    
    with CubeController() as cube:
        cube.rotate_y_cw()        # Spin cube left→front (90° CW from top)
        cube.rotate_x_forward()   # Tumble cube forward (top→front)
        cube.face_turn('R', 'cw') # Turn right face clockwise
        cube.execute('R U R\\'')  # Execute Kociemba solution

Architecture:
    CubeController
    ├── Hardware Layer (servo control, timing)
    ├── State Tracking (gripper positions, RP status, cube orientation)
    ├── Primitives (face_turn, rotate_y_*, rotate_x_*)
    └── High-level API (execute solution strings)

Author: RubikPi + Scotty
Date: 2026-04-03
"""

import sys
import os
import time
from dataclasses import dataclass
from typing import Optional, Dict, Literal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maestro

# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════

GRIPPER_CAL = {
    0: {"A": 400, "B": 1100, "C": 1785, "D": 2420},
    2: {"A": 400, "B": 1040, "C": 1710, "D": 2400},
    6: {"A": 475, "B": 1120, "C": 1800, "D": 2425},
    8: {"A": 450, "B": 1120, "C": 1810, "D": 2425},
}

RP_CAL = {
    1: {"retracted": 1890, "hold": 1055},
    3: {"retracted": 1815, "hold": 1100},
    7: {"retracted": 1875, "hold": 990},
    9: {"retracted": 1880, "hold": 1100},
}

# Gripper → RP mapping
GRIPPER_RP = {0: 1, 2: 3, 6: 7, 8: 9}

# Physical layout: which gripper controls which cube face
# When cube is at standard orientation (White front, Blue top)
GRIPPER_FACE = {0: 'L', 2: 'U', 6: 'R', 8: 'D'}

# Timing (seconds)
TIMING = {
    'gripper_move': 0.8,    # Gripper rotation settle time
    'rp_engage': 2.0,       # RP engagement settle
    'rp_retract': 2.0,      # RP retraction settle (must clear before gripper moves)
    'turn_90': 1.2,         # Face turn 90° settle
    'turn_180': 2.0,        # Face turn 180° settle
    'x_rotation': 2.5,      # X axis rotation settle
    'y_rotation': 2.0,      # Y axis rotation settle
}

# X rotation speeds (synchronized to prevent skew)
X_SPEED = {0: 60, 6: 45}

# ═══════════════════════════════════════════════════════════════════════════
# State Tracking
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CubeOrientation:
    """Track which color is on which face."""
    F: str = 'W'  # Front = White
    B: str = 'Y'  # Back = Yellow
    R: str = 'R'  # Right = Red
    L: str = 'O'  # Left = Orange
    U: str = 'B'  # Up = Blue
    D: str = 'G'  # Down = Green
    
    def y_cw(self):
        """Y rotation 90° CW (from top view): L→F→R→B→L"""
        self.F, self.R, self.B, self.L = self.L, self.F, self.R, self.B
    
    def y_ccw(self):
        """Y rotation 90° CCW (from top view): R→F→L→B→R"""
        self.F, self.L, self.B, self.R = self.R, self.F, self.L, self.B
    
    def y_180(self):
        """Y rotation 180°: F↔B, R↔L"""
        self.F, self.B = self.B, self.F
        self.R, self.L = self.L, self.R
    
    def x_fwd(self):
        """X rotation 90° forward (top tumbles toward camera): U→F→D→B→U"""
        self.F, self.D, self.B, self.U = self.U, self.F, self.D, self.B
    
    def x_back(self):
        """X rotation 90° backward: D→F→U→B→D"""
        self.F, self.U, self.B, self.D = self.D, self.F, self.U, self.B
    
    def x_180(self):
        """X rotation 180°: F↔B, U↔D"""
        self.F, self.B = self.B, self.F
        self.U, self.D = self.D, self.U
    
    def __str__(self):
        return f"F={self.F} B={self.B} R={self.R} L={self.L} U={self.U} D={self.D}"


# ═══════════════════════════════════════════════════════════════════════════
# Main Controller
# ═══════════════════════════════════════════════════════════════════════════

class CubeController:
    """
    Stateful controller for RCubed robot.
    
    Tracks:
    - Gripper positions (A/B/C/D for each of 0, 2, 6, 8)
    - RP status (hold/retracted for each of 1, 3, 7, 9)
    - Cube orientation (which color on which face)
    
    All rotations handle their own prep work automatically.
    """
    
    def __init__(self, port: str = '/dev/ttyACM0', verbose: bool = True):
        self.port = port
        self.verbose = verbose
        self.ctrl: Optional[maestro.Controller] = None
        
        # State tracking
        self.gripper_pos = {0: 'B', 2: 'B', 6: 'B', 8: 'B'}
        self.rp_status = {1: 'retracted', 3: 'retracted', 7: 'retracted', 9: 'retracted'}
        self.cube = CubeOrientation()
        self.move_count = 0
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def connect(self):
        """Connect to Maestro controller."""
        self._log("Connecting to Maestro...")
        self.ctrl = maestro.Controller(self.port)
        # Set acceleration on gripper servos
        for ch in [0, 2, 6, 8]:
            self.ctrl.setAccel(ch, 110)
        self._log("Connected.")
    
    def close(self):
        """Close connection."""
        if self.ctrl:
            self.ctrl.close()
            self.ctrl = None
    
    def _log(self, msg: str):
        if self.verbose:
            print(msg)
    
    # ─── Low-level Hardware ─────────────────────────────────────────────
    
    def _set_gripper(self, servo: int, pos: str):
        """Set gripper servo to position A/B/C/D."""
        us = GRIPPER_CAL[servo][pos]
        self.ctrl.setTarget(servo, us * 4)
        self.gripper_pos[servo] = pos
    
    def _set_rp(self, rp: int, state: str, speed: int = 0):
        """Set RP servo to hold/retracted."""
        self.ctrl.setSpeed(rp, speed)
        us = RP_CAL[rp][state]
        self.ctrl.setTarget(rp, us * 4)
        self.rp_status[rp] = state
    
    def _gripper_for_rp(self, rp: int) -> int:
        """Get gripper servo for an RP servo."""
        return {1: 0, 3: 2, 7: 6, 9: 8}[rp]
    
    def _rp_for_gripper(self, gripper: int) -> int:
        """Get RP servo for a gripper servo."""
        return GRIPPER_RP[gripper]
    
    # ─── RP Control ─────────────────────────────────────────────────────
    
    def engage(self, *grippers: int, slow: bool = True):
        """
        Engage RP for specified grippers (push toward cube).
        Slow engage prevents catching cube edges.
        """
        speed = 30 if slow else 0
        for g in grippers:
            rp = self._rp_for_gripper(g)
            self._set_rp(rp, 'hold', speed)
        time.sleep(TIMING['rp_engage'])
        # Reset speed to fast for future retracts
        for g in grippers:
            self.ctrl.setSpeed(self._rp_for_gripper(g), 0)
    
    def retract(self, *grippers: int):
        """Retract RP for specified grippers (pull away from cube)."""
        for g in grippers:
            rp = self._rp_for_gripper(g)
            self._set_rp(rp, 'retracted', 0)  # Always fast retract
        time.sleep(TIMING['rp_retract'])
    
    def engage_all(self):
        """Engage all 4 RPs."""
        self.engage(0, 2, 6, 8)
    
    def holding_grippers(self) -> list:
        """Return list of grippers currently holding."""
        return [self._gripper_for_rp(rp) for rp, status in self.rp_status.items() if status == 'hold']
    
    # ─── Gripper Movement ───────────────────────────────────────────────
    
    def reset_gripper_to_b(self, gripper: int):
        """Reset a single gripper to B position (requires RP retracted)."""
        if self.gripper_pos[gripper] == 'B':
            return  # Already there
        rp = self._rp_for_gripper(gripper)
        was_holding = self.rp_status[rp] == 'hold'
        if was_holding:
            self.retract(gripper)
        self._set_gripper(gripper, 'B')
        time.sleep(TIMING['gripper_move'])
        if was_holding:
            self.engage(gripper)
    
    def reset_all_to_b(self):
        """Reset all grippers to B position."""
        for g in [0, 2, 6, 8]:
            if self.gripper_pos[g] != 'B':
                self.reset_gripper_to_b(g)
    
    # ─── Prep Helpers ───────────────────────────────────────────────────
    
    def _prep_for_y_rotation(self):
        """
        Prepare for Y rotation (grippers 2&8 rotate).
        Need: 2&8 at B, 3&9 holding, 1&7 retracted.
        """
        # Ensure 0&6 are out of the way
        if self.rp_status[1] == 'hold' or self.rp_status[7] == 'hold':
            # Transfer hold to 3&9 first
            self.engage(2, 8)
            self.retract(0, 6)
        
        # Ensure 3&9 are holding
        if self.rp_status[3] != 'hold' or self.rp_status[9] != 'hold':
            self.engage(2, 8)
        
        # Ensure 1&7 are retracted
        if self.rp_status[1] == 'hold' or self.rp_status[7] == 'hold':
            self.retract(0, 6)
        
        # Ensure 2&8 are at B
        if self.gripper_pos[2] != 'B':
            self.retract(2)
            self._set_gripper(2, 'B')
            time.sleep(TIMING['gripper_move'])
            self.engage(2)
        if self.gripper_pos[8] != 'B':
            self.retract(8)
            self._set_gripper(8, 'B')
            time.sleep(TIMING['gripper_move'])
            self.engage(8)
    
    def _prep_for_x_rotation(self):
        """
        Prepare for X rotation (grippers 0&6 rotate).
        Need: 0&6 at B, 1&7 holding, 3&9 retracted.
        """
        # Ensure 1&7 are holding
        if self.rp_status[1] != 'hold' or self.rp_status[7] != 'hold':
            self.engage(0, 6)
        
        # Ensure 3&9 are retracted
        if self.rp_status[3] == 'hold' or self.rp_status[9] == 'hold':
            self.retract(2, 8)
        
        # Ensure 0&6 are at B
        if self.gripper_pos[0] != 'B':
            self.retract(0)
            self._set_gripper(0, 'B')
            time.sleep(TIMING['gripper_move'])
            self.engage(0)
        if self.gripper_pos[6] != 'B':
            self.retract(6)
            self._set_gripper(6, 'B')
            time.sleep(TIMING['gripper_move'])
            self.engage(6)
    
    # ─── Y Rotations (Spin around vertical axis) ────────────────────────
    
    def rotate_y_cw(self):
        """
        Rotate cube 90° CW (looking from top).
        L→F, F→R, R→B, B→L
        """
        self._log("  Y 90° CW")
        self._prep_for_y_rotation()
        
        # Rotate: 2:B→A, 8:B→C (opposite directions)
        self._set_gripper(2, 'A')
        self._set_gripper(8, 'C')
        time.sleep(TIMING['y_rotation'])
        
        self.cube.y_cw()
    
    def rotate_y_ccw(self):
        """
        Rotate cube 90° CCW (looking from top).
        R→F, F→L, L→B, B→R
        """
        self._log("  Y 90° CCW")
        self._prep_for_y_rotation()
        
        # Rotate: 2:B→C, 8:B→A
        self._set_gripper(2, 'C')
        self._set_gripper(8, 'A')
        time.sleep(TIMING['y_rotation'])
        
        self.cube.y_ccw()
    
    def rotate_y_180(self):
        """
        Rotate cube 180° around Y axis.
        F↔B, R↔L
        """
        self._log("  Y 180°")
        # For 180°, grippers 2&8 can toggle A↔C
        # But they need to be at A or C to start (if at B, do two 90° moves)
        if self.gripper_pos[2] == 'B':
            self.rotate_y_cw()
            self.rotate_y_cw()
        else:
            # Already at A or C, can toggle
            self.engage(2, 8)
            self.retract(0, 6)
            
            new_2 = 'C' if self.gripper_pos[2] == 'A' else 'A'
            new_8 = 'A' if self.gripper_pos[8] == 'C' else 'C'
            self._set_gripper(2, new_2)
            self._set_gripper(8, new_8)
            time.sleep(TIMING['y_rotation'])
            
            self.cube.y_180()
    
    # ─── X Rotations (Tumble forward/backward) ──────────────────────────
    
    def rotate_x_forward(self):
        """
        Rotate cube 90° forward (top tumbles toward camera).
        U→F, F→D, D→B, B→U
        """
        self._log("  X 90° forward")
        self._prep_for_x_rotation()
        
        # Rotate: 0:B→C, 6:B→A (synchronized speeds)
        self.ctrl.setSpeed(0, X_SPEED[0])
        self.ctrl.setSpeed(6, X_SPEED[6])
        self._set_gripper(0, 'C')
        self._set_gripper(6, 'A')
        time.sleep(TIMING['x_rotation'])
        self.ctrl.setSpeed(0, 0)
        self.ctrl.setSpeed(6, 0)
        
        self.cube.x_fwd()
    
    def rotate_x_backward(self):
        """
        Rotate cube 90° backward (bottom tumbles toward camera).
        D→F, F→U, U→B, B→D
        """
        self._log("  X 90° backward")
        self._prep_for_x_rotation()
        
        # Rotate: 0:B→A, 6:B→C
        self.ctrl.setSpeed(0, X_SPEED[0])
        self.ctrl.setSpeed(6, X_SPEED[6])
        self._set_gripper(0, 'A')
        self._set_gripper(6, 'C')
        time.sleep(TIMING['x_rotation'])
        self.ctrl.setSpeed(0, 0)
        self.ctrl.setSpeed(6, 0)
        
        self.cube.x_back()
    
    def rotate_x_180(self):
        """
        Rotate cube 180° around X axis.
        F↔B, U↔D
        """
        self._log("  X 180°")
        # Two forward rotations
        self.rotate_x_forward()
        self._prep_for_x_rotation()  # Reset 0&6 to B
        self.rotate_x_forward()
    
    # ─── Face Turns ─────────────────────────────────────────────────────
    
    def face_turn(self, face: str, direction: Literal['cw', 'ccw', '180']):
        """
        Turn a face.
        
        face: 'R', 'L', 'U', 'D', 'F', or 'B'
        direction: 'cw', 'ccw', or '180'
        
        F and B faces have no gripper - requires cube rotation first.
        """
        self.move_count += 1
        self._log(f"  [{self.move_count}] Face turn: {face} {direction}")
        
        # Map face to gripper
        face_gripper = {'R': 6, 'L': 0, 'U': 2, 'D': 8, 'F': None, 'B': None}
        gripper = face_gripper[face]
        
        if gripper is None:
            # F or B - need cube rotation
            if face == 'F':
                self.rotate_y_cw()
                self._do_face_turn(6, direction)  # F is now at R
                self.rotate_y_ccw()
            else:  # B
                self.rotate_y_ccw()
                self._do_face_turn(6, direction)  # B is now at R
                self.rotate_y_cw()
        else:
            self._do_face_turn(gripper, direction)
    
    def _do_face_turn(self, gripper: int, direction: Literal['cw', 'ccw', '180']):
        """Execute face turn on a gripper. Requires all RPs holding, all at B."""
        # Ensure all RPs holding
        if len(self.holding_grippers()) < 4:
            self.engage_all()
        
        # Ensure all at B
        self.reset_all_to_b()
        
        # Target position
        target = {'cw': 'C', 'ccw': 'A', '180': 'D'}[direction]
        delay = TIMING['turn_180'] if direction == '180' else TIMING['turn_90']
        
        # Turn
        self._set_gripper(gripper, target)
        time.sleep(delay)
        
        # Reset to B
        self.retract(gripper)
        self._set_gripper(gripper, 'B')
        time.sleep(TIMING['gripper_move'])
        self.engage(gripper)
    
    # ─── Solution Execution ─────────────────────────────────────────────
    
    def execute(self, solution: str):
        """
        Execute a Kociemba solution string.
        e.g., "R U R' F2 B L2"
        """
        moves = solution.strip().split()
        total = len(moves)
        
        self._log(f"\n═══ EXECUTING: {solution} ═══")
        self._log(f"    Total moves: {total}\n")
        
        # Setup: all at B, all holding
        self.reset_all_to_b()
        self.engage_all()
        
        for i, move in enumerate(moves):
            self._log(f"\n── Move {i+1}/{total}: {move} ──")
            self._execute_move(move)
        
        self._log(f"\n═══ COMPLETE ({self.move_count} total operations) ═══")
    
    def _execute_move(self, move: str):
        """Execute a single move (R, R', R2, etc.)"""
        face = move[0]
        if len(move) == 1:
            direction = 'cw'
        elif move[1] == "'":
            direction = 'ccw'
        elif move[1] == "2":
            direction = '180'
        else:
            raise ValueError(f"Unknown move: {move}")
        
        self.face_turn(face, direction)
    
    # ─── Status ─────────────────────────────────────────────────────────
    
    def status(self):
        """Print current state."""
        print(f"Cube orientation: {self.cube}")
        print(f"Gripper positions: {self.gripper_pos}")
        print(f"RP status: {self.rp_status}")
        print(f"Move count: {self.move_count}")


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="RCubed Cube Controller")
    parser.add_argument('command', nargs='?', help='Command or solution string')
    parser.add_argument('--port', default='/dev/ttyACM0')
    args = parser.parse_args()
    
    with CubeController(port=args.port) as cube:
        cube.engage_all()
        
        if args.command:
            if args.command.upper() in ['Y_CW', 'Y_CCW', 'Y_180', 'X_FWD', 'X_BACK', 'X_180']:
                # Single rotation
                cmd = args.command.upper()
                if cmd == 'Y_CW': cube.rotate_y_cw()
                elif cmd == 'Y_CCW': cube.rotate_y_ccw()
                elif cmd == 'Y_180': cube.rotate_y_180()
                elif cmd == 'X_FWD': cube.rotate_x_forward()
                elif cmd == 'X_BACK': cube.rotate_x_backward()
                elif cmd == 'X_180': cube.rotate_x_180()
            else:
                # Solution string
                cube.execute(args.command)
        
        cube.status()


if __name__ == '__main__':
    main()
