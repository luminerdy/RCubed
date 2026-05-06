#!/usr/bin/env python3
"""
RCubed Cube Controller - Standard Notation with Optimized Execution
====================================================================

Uses standard cube notation (R, R', R2, x, y, z).
Automatically handles F/B moves by rotating cube to use R gripper.
Optimizes consecutive F/B moves to minimize rotations.

Usage:
    from cube_controller import CubeController
    
    with CubeController() as cube:
        # Individual moves
        cube.R()    # Right CW
        cube.Rp()   # Right CCW (prime)
        cube.R2()   # Right 180
        cube.F()    # Front CW (auto-rotates cube)
        
        # Whole cube rotations
        cube.x()    # Tumble forward (top → front)
        cube.y()    # Spin right (left → front... no wait, F→L)
        
        # Execute solution (optimized)
        cube.execute("R U R' F2 B L2")

Author: RubikPi + Scotty
Date: 2026-04-03
"""

import sys
import os
import time
from dataclasses import dataclass, field
from typing import Optional, Literal, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maestro
import robot_state

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

GRIPPER_RP = {0: 1, 2: 3, 6: 7, 8: 9}

TIMING = {
    'gripper_move': 0.8,
    'rp_engage': 2.0,
    'rp_retract': 2.0,
    'turn_90': 1.2,
    'turn_180': 2.0,
    'x_rotation': 2.5,
    'y_rotation': 2.0,
}

X_SPEED = {0: 60, 6: 45}

# ═══════════════════════════════════════════════════════════════════════════
# Cube Orientation Tracking
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CubeOrientation:
    """Track which color is on which face."""
    F: str = 'W'
    B: str = 'Y'
    R: str = 'R'
    L: str = 'O'
    U: str = 'B'
    D: str = 'G'
    
    def y(self):
        """y rotation (standard): R→F, F→L, L→B, B→R (right comes to front)"""
        self.F, self.L, self.B, self.R = self.R, self.F, self.L, self.B
    
    def yp(self):
        """y' rotation (standard): L→F, F→R, R→B, B→L (left comes to front)"""
        self.F, self.R, self.B, self.L = self.L, self.F, self.R, self.B
    
    def y2(self):
        self.F, self.B = self.B, self.F
        self.R, self.L = self.L, self.R
    
    def x(self):
        """x rotation (standard): U→F, F→D, D→B, B→U (top tumbles toward you)"""
        self.F, self.D, self.B, self.U = self.U, self.F, self.D, self.B
    
    def xp(self):
        """x' rotation (standard): D→F, F→U, U→B, B→D (bottom tumbles toward you)"""
        self.F, self.U, self.B, self.D = self.D, self.F, self.U, self.B
    
    def x2(self):
        self.F, self.B = self.B, self.F
        self.U, self.D = self.D, self.U
    
    def z(self):
        """z rotation: same as F move direction. U→L, L→D, D→R, R→U"""
        self.U, self.L, self.D, self.R = self.R, self.U, self.L, self.D
    
    def zp(self):
        """z' rotation"""
        self.U, self.R, self.D, self.L = self.L, self.U, self.R, self.D
    
    def z2(self):
        self.U, self.D = self.D, self.U
        self.R, self.L = self.L, self.R
    
    def __str__(self):
        return f"F={self.F} B={self.B} R={self.R} L={self.L} U={self.U} D={self.D}"


# ═══════════════════════════════════════════════════════════════════════════
# Main Controller
# ═══════════════════════════════════════════════════════════════════════════

class CubeController:
    """
    Stateful controller with standard cube notation.
    
    Grippers: 0=L, 2=U, 6=R, 8=D (no gripper on F/B)
    F/B moves handled by rotating cube to use R gripper.
    """
    
    def __init__(self, port: str = '/dev/ttyACM0', verbose: bool = True):
        self.port = port
        self.verbose = verbose
        self.ctrl: Optional[maestro.Controller] = None

        # Restore state from previous script if available
        saved = robot_state.load()
        if saved:
            self.gripper_pos = saved['grippers']
            self.rp_status   = saved['rp']
            self._needs_safe_startup = False
        else:
            self.gripper_pos = {0: 'B', 2: 'B', 6: 'B', 8: 'B'}
            self.rp_status   = {1: 'retracted', 3: 'retracted', 7: 'retracted', 9: 'retracted'}
            self._needs_safe_startup = True

        # Cube state
        self.cube = CubeOrientation()
        self.robot_orientation = 'normal'  # 'normal', 'y', or 'yp'

        self.move_count = 0
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            robot_state.invalidate()
        self.close()
        return False  # don't suppress exceptions
    
    def connect(self):
        self._log("Connecting...")
        self.ctrl = maestro.Controller(self.port)
        for ch in [0, 2, 6, 8]:
            self.ctrl.setAccel(ch, 110)
        if self._needs_safe_startup:
            self._safe_startup()
            self._needs_safe_startup = False
        else:
            self._log("State restored — skipping safe startup.")
        self._log("Connected.")
    
    def close(self):
        if self.ctrl:
            robot_state.save(self.gripper_pos, self.rp_status)
            self.ctrl.close()
            self.ctrl = None
    
    def _log(self, msg: str):
        if self.verbose:
            print(msg)
    
    # ─── Safe Startup ───────────────────────────────────────────────────

    def _safe_startup(self):
        """
        One-time reset when state is unknown (first run, power-on, or crash recovery).

        Strategy:
          1. Retract all RPs fast → max physical clearance between fingers
          2. Move opposite pairs to B simultaneously (non-adjacent, can't collide):
             - 0 & 6 (left/right) together
             - 2 & 8 (top/bottom) together — safe once 0&6 are at B
        """
        self._log("State unknown — safe startup...")

        # Step 1: Retract all RPs (fast) for maximum clearance
        for rp in [1, 3, 7, 9]:
            self.ctrl.setSpeed(rp, 0)
            self.ctrl.setTarget(rp, RP_CAL[rp]['retracted'] * 4)
            self.rp_status[rp] = 'retracted'
        time.sleep(TIMING['rp_retract'])

        # Step 2: Move left/right (non-adjacent) to B simultaneously
        self._set_gripper(0, 'B')
        self._set_gripper(6, 'B')
        time.sleep(TIMING['gripper_move'] + 0.5)

        # Step 3: Move top/bottom to B — 0&6 at B so any 2/8 position is now safe
        self._set_gripper(2, 'B')
        self._set_gripper(8, 'B')
        time.sleep(TIMING['gripper_move'] + 0.5)

        self._log("Safe startup complete.")

    # ─── Low-level Hardware ─────────────────────────────────────────────
    
    def _set_gripper(self, servo: int, pos: str):
        us = GRIPPER_CAL[servo][pos]
        self.ctrl.setTarget(servo, us * 4)
        self.gripper_pos[servo] = pos
    
    def _set_rp(self, rp: int, state: str, speed: int = 0):
        self.ctrl.setSpeed(rp, speed)
        us = RP_CAL[rp][state]
        self.ctrl.setTarget(rp, us * 4)
        self.rp_status[rp] = state
    
    # ─── RP Control ─────────────────────────────────────────────────────
    
    def engage(self, *grippers: int, slow: bool = True):
        speed = 30 if slow else 0
        for g in grippers:
            rp = GRIPPER_RP[g]
            self._set_rp(rp, 'hold', speed)
        time.sleep(TIMING['rp_engage'])
        for g in grippers:
            self.ctrl.setSpeed(GRIPPER_RP[g], 0)
    
    def retract(self, *grippers: int):
        for g in grippers:
            rp = GRIPPER_RP[g]
            self._set_rp(rp, 'retracted', 0)
        time.sleep(TIMING['rp_retract'])
    
    def engage_all(self):
        self.engage(0, 2, 6, 8)
    
    def _holding(self) -> list:
        return [g for g, rp in GRIPPER_RP.items() if self.rp_status[rp] == 'hold']
    
    # ─── Gripper Helpers ────────────────────────────────────────────────
    
    def _reset_gripper(self, g: int):
        """Reset gripper to B if not already there."""
        if self.gripper_pos[g] == 'B':
            return
        rp = GRIPPER_RP[g]
        was_holding = self.rp_status[rp] == 'hold'
        if was_holding:
            self.retract(g)
        self._set_gripper(g, 'B')
        time.sleep(TIMING['gripper_move'])
        if was_holding:
            self.engage(g)
    
    def _reset_all(self):
        for g in [0, 2, 6, 8]:
            self._reset_gripper(g)
    
    def _ensure_holding(self):
        if len(self._holding()) < 4:
            self.engage_all()
    
    # ─── Y Rotation Primitives ──────────────────────────────────────────
    
    def _prep_y(self):
        """Prep for Y rotation: 3&9 hold, 1&7 retract, 2&8 at B."""
        # Ensure 3&9 holding
        if self.rp_status[3] != 'hold' or self.rp_status[9] != 'hold':
            self.engage(2, 8)
        # Retract 1&7
        if self.rp_status[1] == 'hold' or self.rp_status[7] == 'hold':
            self.retract(0, 6)
        # Reset 2&8 to B
        for g in [2, 8]:
            if self.gripper_pos[g] != 'B':
                self.retract(g)
                self._set_gripper(g, 'B')
                time.sleep(TIMING['gripper_move'])
                self.engage(g)
    
    def _do_y(self):
        """Physical y rotation (standard): 2:B→C, 8:B→A (right to front)"""
        self._prep_y()
        self._set_gripper(2, 'C')
        self._set_gripper(8, 'A')
        time.sleep(TIMING['y_rotation'])
    
    def _do_yp(self):
        """Physical y' rotation (standard): 2:B→A, 8:B→C (left to front)"""
        self._prep_y()
        self._set_gripper(2, 'A')
        self._set_gripper(8, 'C')
        time.sleep(TIMING['y_rotation'])
    
    def _do_y2(self):
        """Physical y2 rotation."""
        # Toggle 2&8 between A↔C
        self._prep_y()
        if self.gripper_pos[2] == 'B':
            # Do two y moves
            self._do_y()
            self._prep_y()
            self._do_y()
        else:
            new_2 = 'C' if self.gripper_pos[2] == 'A' else 'A'
            new_8 = 'A' if self.gripper_pos[8] == 'C' else 'C'
            self._set_gripper(2, new_2)
            self._set_gripper(8, new_8)
            time.sleep(TIMING['y_rotation'])
    
    # ─── X Rotation Primitives ──────────────────────────────────────────
    
    def _prep_x(self):
        """Prep for X rotation: 1&7 hold, 3&9 retract, 0&6 at B."""
        if self.rp_status[1] != 'hold' or self.rp_status[7] != 'hold':
            self.engage(0, 6)
        if self.rp_status[3] == 'hold' or self.rp_status[9] == 'hold':
            self.retract(2, 8)
        for g in [0, 6]:
            if self.gripper_pos[g] != 'B':
                self.retract(g)
                self._set_gripper(g, 'B')
                time.sleep(TIMING['gripper_move'])
                self.engage(g)
    
    def _do_x(self):
        """Physical x rotation: 0:B→C, 6:B→A"""
        self._prep_x()
        self.ctrl.setSpeed(0, X_SPEED[0])
        self.ctrl.setSpeed(6, X_SPEED[6])
        self._set_gripper(0, 'C')
        self._set_gripper(6, 'A')
        time.sleep(TIMING['x_rotation'])
        self.ctrl.setSpeed(0, 0)
        self.ctrl.setSpeed(6, 0)
    
    def _do_xp(self):
        """Physical x' rotation: 0:B→A, 6:B→C"""
        self._prep_x()
        self.ctrl.setSpeed(0, X_SPEED[0])
        self.ctrl.setSpeed(6, X_SPEED[6])
        self._set_gripper(0, 'A')
        self._set_gripper(6, 'C')
        time.sleep(TIMING['x_rotation'])
        self.ctrl.setSpeed(0, 0)
        self.ctrl.setSpeed(6, 0)
    
    def _do_x2(self):
        """Physical x2: two x moves."""
        self._do_x()
        self._prep_x()
        self._do_x()
    
    # ─── Face Turn Primitive ────────────────────────────────────────────
    
    def _turn(self, gripper: int, direction: str):
        """
        Turn a face using specified gripper.
        direction: 'cw', 'ccw', '180'
        All grippers: CW=B→C, CCW=B→A, 180=B→D
        """
        self._ensure_holding()
        self._reset_all()
        
        target = {'cw': 'C', 'ccw': 'A', '180': 'D'}[direction]
        delay = TIMING['turn_180'] if direction == '180' else TIMING['turn_90']
        
        self._set_gripper(gripper, target)
        time.sleep(delay)
        
        # Reset to B
        self.retract(gripper)
        self._set_gripper(gripper, 'B')
        time.sleep(TIMING['gripper_move'])
        self.engage(gripper)
    
    # ─── Robot Orientation Management ───────────────────────────────────
    
    def _transition_to(self, target: str):
        """
        Transition robot to target orientation.
        target: 'normal', 'y', 'yp'
        
        'normal' = standard (F at front, camera sees F)
        'y' = after y rotation: B is at R gripper (for B moves)
        'yp' = after y' rotation: F is at R gripper (for F moves)
        """
        current = self.robot_orientation
        if current == target:
            return
        
        self._log(f"  [transition {current} → {target}]")
        
        if current == 'normal':
            if target == 'y':
                self._do_y()
            elif target == 'yp':
                self._do_yp()
        elif current == 'y':
            if target == 'normal':
                self._do_yp()
            elif target == 'yp':
                self._do_y2()
        elif current == 'yp':
            if target == 'normal':
                self._do_y()
            elif target == 'y':
                self._do_y2()
        
        self.robot_orientation = target
    
    def _orientation_for_face(self, face: str) -> str:
        """What robot orientation is needed to turn this face?"""
        if face in ['R', 'L', 'U', 'D']:
            return 'normal'
        elif face == 'F':
            return 'y'   # y rotation puts F at R position
        elif face == 'B':
            return 'yp'  # y' rotation puts B at R position
        return 'normal'
    
    def _gripper_for_face(self, face: str, orientation: str) -> int:
        """Which gripper controls this face given current orientation?"""
        if orientation == 'normal':
            return {'R': 6, 'L': 0, 'U': 2, 'D': 8}[face]
        elif orientation == 'y':
            # After y: F→L, R→F, B→R, L→B
            # So F (now at L) uses gripper 0... wait no
            # We rotated so original F is at R gripper position
            return 6  # F is now at R
        elif orientation == 'yp':
            # After y': original B is at R gripper position
            return 6  # B is now at R
        return 6
    
    # ═══════════════════════════════════════════════════════════════════
    # PUBLIC API - Standard Cube Notation
    # ═══════════════════════════════════════════════════════════════════
    
    # ─── Whole Cube Rotations ───────────────────────────────────────────
    
    def x(self):
        """x rotation (R direction): top tumbles toward you."""
        self._log("  x")
        self._do_x()
        self.cube.x()
        self.move_count += 1
    
    def xp(self):
        """x' rotation: bottom tumbles toward you."""
        self._log("  x'")
        self._do_xp()
        self.cube.xp()
        self.move_count += 1
    
    def x2(self):
        """x2 rotation."""
        self._log("  x2")
        self._do_x2()
        self.cube.x2()
        self.move_count += 1
    
    def y(self):
        """y rotation (U direction): F→L, R→F."""
        self._log("  y")
        self._do_y()
        self.cube.y()
        self.move_count += 1
    
    def yp(self):
        """y' rotation: F→R, L→F."""
        self._log("  y'")
        self._do_yp()
        self.cube.yp()
        self.move_count += 1
    
    def y2(self):
        """y2 rotation."""
        self._log("  y2")
        self._do_y2()
        self.cube.y2()
        self.move_count += 1
    
    # Note: z rotations would require different gripper choreography
    # Not implemented yet - would need grippers 0&6 to rotate together
    
    # ─── Face Turns ─────────────────────────────────────────────────────
    
    def R(self):
        self._log("  R")
        self._transition_to('normal')
        self._turn(6, 'cw')
        self.move_count += 1
    
    def Rp(self):
        self._log("  R'")
        self._transition_to('normal')
        self._turn(6, 'ccw')
        self.move_count += 1
    
    def R2(self):
        self._log("  R2")
        self._transition_to('normal')
        self._turn(6, '180')
        self.move_count += 1
    
    def L(self):
        self._log("  L")
        self._transition_to('normal')
        self._turn(0, 'cw')
        self.move_count += 1
    
    def Lp(self):
        self._log("  L'")
        self._transition_to('normal')
        self._turn(0, 'ccw')
        self.move_count += 1
    
    def L2(self):
        self._log("  L2")
        self._transition_to('normal')
        self._turn(0, '180')
        self.move_count += 1
    
    def U(self):
        self._log("  U")
        self._transition_to('normal')
        self._turn(2, 'cw')
        self.move_count += 1
    
    def Up(self):
        self._log("  U'")
        self._transition_to('normal')
        self._turn(2, 'ccw')
        self.move_count += 1
    
    def U2(self):
        self._log("  U2")
        self._transition_to('normal')
        self._turn(2, '180')
        self.move_count += 1
    
    def D(self):
        self._log("  D")
        self._transition_to('normal')
        self._turn(8, 'cw')
        self.move_count += 1
    
    def Dp(self):
        self._log("  D'")
        self._transition_to('normal')
        self._turn(8, 'ccw')
        self.move_count += 1
    
    def D2(self):
        self._log("  D2")
        self._transition_to('normal')
        self._turn(8, '180')
        self.move_count += 1
    
    def F(self):
        self._log("  F")
        self._transition_to('yp')  # y' puts F at R gripper
        self._turn(6, 'cw')
        self.move_count += 1
    
    def Fp(self):
        self._log("  F'")
        self._transition_to('yp')
        self._turn(6, 'ccw')
        self.move_count += 1
    
    def F2(self):
        self._log("  F2")
        self._transition_to('yp')
        self._turn(6, '180')
        self.move_count += 1
    
    def B(self):
        self._log("  B")
        self._transition_to('y')  # y puts B at R gripper
        self._turn(6, 'cw')
        self.move_count += 1
    
    def Bp(self):
        self._log("  B'")
        self._transition_to('y')
        self._turn(6, 'ccw')
        self.move_count += 1
    
    def B2(self):
        self._log("  B2")
        self._transition_to('y')
        self._turn(6, '180')
        self.move_count += 1
    
    # ─── Solution Execution ─────────────────────────────────────────────
    
    def execute(self, solution: str):
        """
        Execute a Kociemba solution string.
        Optimizes rotations - only transitions when needed.
        
        Example: "R U R' F2 B L2"
        """
        moves = self._parse_solution(solution)
        total = len(moves)
        
        self._log(f"\n═══ EXECUTING: {solution} ═══")
        self._log(f"    {total} moves\n")
        
        # Setup
        self._ensure_holding()
        self._reset_all()
        
        for i, (face, direction) in enumerate(moves):
            self._log(f"\n── {i+1}/{total}: {face}{self._dir_symbol(direction)} ──")
            
            # Get method and call it
            method = self._get_move_method(face, direction)
            method()
        
        # Return to normal orientation at end
        self._transition_to('normal')
        
        self._log(f"\n═══ COMPLETE ({self.move_count} operations) ═══")
    
    def _parse_solution(self, solution: str) -> List[Tuple[str, str]]:
        """Parse solution string into (face, direction) tuples."""
        moves = []
        for token in solution.strip().split():
            face = token[0]
            if len(token) == 1:
                direction = 'cw'
            elif token[1] == "'":
                direction = 'ccw'
            elif token[1] == "2":
                direction = '180'
            else:
                raise ValueError(f"Unknown move: {token}")
            moves.append((face, direction))
        return moves
    
    def _dir_symbol(self, direction: str) -> str:
        return {'cw': '', 'ccw': "'", '180': '2'}[direction]
    
    def _get_move_method(self, face: str, direction: str):
        """Get the method for a face+direction."""
        method_map = {
            ('R', 'cw'): self.R, ('R', 'ccw'): self.Rp, ('R', '180'): self.R2,
            ('L', 'cw'): self.L, ('L', 'ccw'): self.Lp, ('L', '180'): self.L2,
            ('U', 'cw'): self.U, ('U', 'ccw'): self.Up, ('U', '180'): self.U2,
            ('D', 'cw'): self.D, ('D', 'ccw'): self.Dp, ('D', '180'): self.D2,
            ('F', 'cw'): self.F, ('F', 'ccw'): self.Fp, ('F', '180'): self.F2,
            ('B', 'cw'): self.B, ('B', 'ccw'): self.Bp, ('B', '180'): self.B2,
        }
        return method_map[(face, direction)]
    
    # ─── Status ─────────────────────────────────────────────────────────
    
    def status(self):
        """Print current state."""
        print(f"Cube: {self.cube}")
        print(f"Robot orientation: {self.robot_orientation}")
        print(f"Grippers: {self.gripper_pos}")
        print(f"RPs: {self.rp_status}")
        print(f"Moves: {self.move_count}")


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="RCubed Cube Controller")
    parser.add_argument('moves', nargs='*', help='Moves or solution string')
    parser.add_argument('--port', default='/dev/ttyACM0')
    args = parser.parse_args()
    
    if not args.moves:
        print("Usage:")
        print("  python3 cube_controller.py R U R'     # Individual moves")
        print("  python3 cube_controller.py \"R U R'\"   # Solution string")
        print("  python3 cube_controller.py x y        # Cube rotations")
        return
    
    with CubeController(port=args.port) as cube:
        cube.engage_all()
        
        # Join args into solution string
        solution = ' '.join(args.moves)
        cube.execute(solution)
        
        cube.status()


if __name__ == '__main__':
    main()
