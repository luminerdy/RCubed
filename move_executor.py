#!/usr/bin/env python3
"""
RCubed Move Executor
Translates Kociemba solution notation to servo choreography.

Physical layout:
  Gripper 0 (servo 0, RP 1) = Left face
  Gripper 2 (servo 2, RP 3) = Up face
  Gripper 6 (servo 6, RP 7) = Right face
  Gripper 8 (servo 8, RP 9) = Down face
  Front face = camera side (no gripper)
  Back face = behind (no gripper)

Gripper positions A,B,C,D (~90° apart):
  A→B→C→D = CW from cube's perspective (looking at the face)
  CW = B→C, CCW = B→A, 180° = B→D
  Verified 2026-03-06 on all servos (0, 2, 6, 8)

CRITICAL: Gripper clearance rules (physical finger geometry):
  - Gripper 0 or 6 can only rotate when 2 and 8 are at B or D
  - Gripper 2 or 8 can only rotate when 0 and 6 are at B or D
  - All grippers MUST be at B before and after each primitive operation

For F/B moves (no gripper): cube rotation + R/L turn + rotate back.
"""

import sys
import os
import time

sys.stdout.reconfigure(line_buffering=True)  # flush output immediately

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maestro

# ─── Servo Config ────────────────────────────────────────────────────────────

GRIPPER = {
    0: {"A": 400, "B": 1100, "C": 1785, "D": 2420},
    2: {"A": 400, "B": 1040, "C": 1710, "D": 2400},
    6: {"A": 475, "B": 1120, "C": 1800, "D": 2425},
    8: {"A": 450, "B": 1120, "C": 1810, "D": 2425},
}

RP = {
    1: {"retracted": 1890, "hold": 1065},
    3: {"retracted": 1815, "hold": 1100},
    7: {"retracted": 1875, "hold": 1000},
    9: {"retracted": 1880, "hold": 1100},
}

# Gripper servo → RP servo mapping
GRIPPER_TO_RP = {0: 1, 2: 3, 6: 7, 8: 9}

# Kociemba face → gripper servo (None = no gripper, needs cube rotation)
FACE_TO_GRIPPER = {
    'U': 2, 'D': 8, 'L': 0, 'R': 6,
    'F': None, 'B': None,
}

GRIPPER_ACCEL = 110
MOVE_DELAY = 0.6       # wait after gripper move
RP_DELAY = 2.0         # wait after RP retract (must fully clear before gripper moves)
RP_SLOW_SPEED = 30     # slow speed for engaging (avoids catching cube edge)
RP_NORMAL_SPEED = 0    # unrestricted
RP_ENGAGE_DELAY = 1.5  # extra time for slow engagement
TURN_DELAY_90 = 1.2    # wait after 90° face turn (CW/CCW)
TURN_DELAY_180 = 2.0   # wait after 180° face turn (needs more settling time)
ROTATE_DELAY = 0.8     # wait after cube rotation

# ─── Low-level servo control ────────────────────────────────────────────────

class CubeController:
    def __init__(self, port='/dev/ttyACM0'):
        self.ctrl = maestro.Controller(port)
        for ch in [0, 2, 6, 8]:
            self.ctrl.setAccel(ch, GRIPPER_ACCEL)
        self.move_count = 0
    
    def close(self):
        self.ctrl.close()
    
    def _set_gripper(self, servo, pos_name):
        us = GRIPPER[servo][pos_name]
        self.ctrl.setTarget(servo, us * 4)
    
    def _set_rp(self, rp_servo, pos_name):
        us = RP[rp_servo][pos_name]
        self.ctrl.setTarget(rp_servo, us * 4)
    
    def _engage(self, gripper, slow=True):
        """Engage RP for a gripper (push toward cube). Slow to avoid catching edges."""
        rp = GRIPPER_TO_RP[gripper]
        if slow:
            self.ctrl.setSpeed(rp, RP_SLOW_SPEED)
        self._set_rp(rp, "hold")
        if slow:
            time.sleep(RP_ENGAGE_DELAY)
            self.ctrl.setSpeed(rp, RP_NORMAL_SPEED)
    
    def _retract(self, gripper):
        """Retract RP for a gripper (pull away from cube). Always at full speed."""
        rp = GRIPPER_TO_RP[gripper]
        self.ctrl.setSpeed(rp, RP_NORMAL_SPEED)  # ensure fast retract
        self._set_rp(rp, "retracted")
    
    def _engage_simultaneous(self, *grippers, slow=True):
        """Engage multiple RP servos at the same time, then wait once."""
        for g in grippers:
            rp = GRIPPER_TO_RP[g]
            if slow:
                self.ctrl.setSpeed(rp, RP_SLOW_SPEED)
            self._set_rp(rp, "hold")
        if slow:
            time.sleep(RP_ENGAGE_DELAY)
            for g in grippers:
                self.ctrl.setSpeed(GRIPPER_TO_RP[g], RP_NORMAL_SPEED)
    
    def _engage_all(self):
        self._engage_simultaneous(0, 2, 6, 8)
    
    # SAFETY: Never retract all. Always keep at least 2 grippers holding.
    # _retract_all is intentionally removed.

    # ─── Face Turn Primitive ─────────────────────────────────────────────

    def face_turn(self, gripper, direction):
        """
        Turn a face. All grippers start at B, all RP in hold.
        
        gripper: 0, 2, 6, or 8
        direction: 'cw', 'ccw', or '180'
        
        ALL servos follow the same pattern (verified 2026-03-06):
        - CW = B→C (A→B→C→D is clockwise from face perspective)
        - CCW = B→A (D→C→B→A is counter-clockwise)
        - 180° = B→D
        """
        # All servos use same mapping (verified with physical testing)
        target = {'cw': 'C', 'ccw': 'A', '180': 'D'}[direction]
        others = [g for g in [0, 2, 6, 8] if g != gripper]
        
        self.move_count += 1
        label = {0: 'L', 2: 'U', 6: 'R', 8: 'D'}[gripper]
        print(f"  [{self.move_count}] Face turn: {label} {direction}")
        
        # All RP should be holding. Gripper rotates, turning the face.
        self._set_gripper(gripper, target)
        # 180° turns need more time to settle before retraction
        delay = TURN_DELAY_180 if direction == '180' else TURN_DELAY_90
        time.sleep(delay)
        
        # Reset gripper back to B:
        # 1. Retract this gripper (pull away)
        self._retract(gripper)
        time.sleep(RP_DELAY)
        
        # 2. Move gripper back to B (free air)
        self._set_gripper(gripper, "B")
        time.sleep(MOVE_DELAY)
        
        # 3. Re-engage (extra 0.2s settling after 180° turns)
        if direction == '180':
            time.sleep(0.2)
        self._engage(gripper)
        time.sleep(RP_DELAY)

    # ─── Cube Rotation Primitive ─────────────────────────────────────────

    def cube_rotate_y(self, direction):
        """
        Rotate entire cube around U-D axis (y rotation).
        Uses grippers 2 (top) and 8 (bottom).
        
        direction: 'cw' (F→R looking from top) or 'ccw' (F→L looking from top)
        
        CW from top: servo 2 B→A, servo 8 B→C (opposite servo directions)
        CCW from top: servo 2 B→C, servo 8 B→A
        
        RULE: Engage new grippers BEFORE retracting old. Always >= 2 holding.
        """
        print(f"  [~] Cube rotation y {direction}")
        
        if direction == 'cw':
            s2_target, s8_target = 'A', 'C'
        else:
            s2_target, s8_target = 'C', 'A'
        
        # State: all 4 hold at B. Need 0&6 retracted for rotation.
        # Retract 0&6 (2&8 still hold = 2 grippers)
        self._retract(0)
        self._retract(6)
        time.sleep(RP_DELAY)
        
        # Rotate cube (2&8 hold)
        self._set_gripper(2, s2_target)
        self._set_gripper(8, s8_target)
        time.sleep(ROTATE_DELAY)
        
        # Transfer: engage 0&6 SIMULTANEOUSLY, then retract 2&8
        self._engage_simultaneous(0, 6)
        time.sleep(0.5)  # settle — let 1&7 fully grip before releasing
        # Now 4 hold. Safe to retract 2&8.
        self._retract(2)
        self._retract(8)
        time.sleep(RP_DELAY)
        
        # Reset 2&8 to B
        self._set_gripper(2, "B")
        self._set_gripper(8, "B")
        time.sleep(MOVE_DELAY)
        
        # Re-engage 2&8 simultaneously (0&6 still hold)
        self._engage_simultaneous(2, 8)
        time.sleep(0.3)  # settle before next operation

    # ─── High-level Move Execution ───────────────────────────────────────

    def execute_move(self, move):
        """
        Execute a single Kociemba move (e.g., "R", "R'", "R2", "F", "B2").
        """
        # Parse move
        face = move[0]
        if len(move) == 1:
            direction = 'cw'
        elif move[1] == "'":
            direction = 'ccw'
        elif move[1] == "2":
            direction = '180'
        else:
            raise ValueError(f"Unknown move: {move}")
        
        gripper = FACE_TO_GRIPPER[face]
        
        if gripper is not None:
            # Direct face turn
            self.face_turn(gripper, direction)
        elif face == 'F':
            # F move: rotate cube so F goes to R, turn R, rotate back
            self.cube_rotate_y('cw')
            self.face_turn(6, direction)  # R gripper = original F
            self.cube_rotate_y('ccw')
        elif face == 'B':
            # B move: rotate cube so B goes to R, turn R, rotate back
            self.cube_rotate_y('ccw')
            self.face_turn(6, direction)  # R gripper = original B
            self.cube_rotate_y('cw')

    def execute_solution(self, solution_string):
        """
        Execute a full Kociemba solution string.
        e.g., "R2 U' F L2 D B2"
        """
        moves = solution_string.strip().split()
        total = len(moves)
        
        print(f"\n═══ EXECUTING SOLUTION: {solution_string} ═══")
        print(f"    Total moves: {total}\n")
        
        # Ensure starting state: all grippers at B, all RP holding
        print("  Setting up: all grippers B, all RP hold")
        for g in [0, 2, 6, 8]:
            self._set_gripper(g, "B")
        time.sleep(MOVE_DELAY)
        self._engage_all()
        time.sleep(RP_DELAY)
        
        for i, move in enumerate(moves):
            print(f"\n── Move {i+1}/{total}: {move} ──")
            self.execute_move(move)
        
        print(f"\n═══ SOLUTION COMPLETE ({self.move_count} servo moves) ═══")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="RCubed Move Executor")
    parser.add_argument('solution', nargs='?', help='Kociemba solution string')
    parser.add_argument('--test', action='store_true', help='Test single move')
    parser.add_argument('--move', type=str, help='Single move to test (e.g., R, U2, F\')')
    parser.add_argument('--port', default='/dev/ttyACM0', help='Maestro port')
    args = parser.parse_args()
    
    cc = CubeController(args.port)
    
    try:
        if args.test and args.move:
            print(f"Testing single move: {args.move}")
            # First ensure all RP hold
            cc._engage_all()
            time.sleep(0.5)
            cc.execute_move(args.move)
        elif args.solution:
            cc.execute_solution(args.solution)
        else:
            print("Usage: python3 move_executor.py 'R2 U F L2'")
            print("       python3 move_executor.py --test --move R")
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted!")
    finally:
        cc.close()
        print("Done.")


if __name__ == "__main__":
    main()
