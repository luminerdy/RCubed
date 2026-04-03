#!/usr/bin/env python3
"""
RCubed Move Executor v2 - With Orientation Tracking
Translates Kociemba solution notation to servo choreography.

New in v2:
- Tracks cube orientation state (which color is front/up)
- Optimizes F/B move sequences (avoids redundant rotations)
- Only rotates back to standard orientation at the end

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

For F/B moves (no gripper): cube rotation + R/L turn (now with tracking).
"""

import sys
import os
import time

sys.stdout.reconfigure(line_buffering=True)

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

GRIPPER_TO_RP = {0: 1, 2: 3, 6: 7, 8: 9}

GRIPPER_ACCEL = 110
MOVE_DELAY = 0.6
RP_DELAY = 2.0
RP_SLOW_SPEED = 30
RP_NORMAL_SPEED = 0
RP_ENGAGE_DELAY = 1.5
TURN_DELAY_90 = 1.2   # For CW/CCW (90° turns)
TURN_DELAY_180 = 2.0  # For 180° turns (needs more time)
ROTATE_DELAY = 0.8

# ─── Orientation Tracking ────────────────────────────────────────────────────

class Orientation:
    """Track which face is currently at each position."""
    def __init__(self):
        # Standard starting orientation: White front, Blue up
        self.front = 'F'  # White
        self.back = 'B'   # Yellow
        self.left = 'L'   # Orange
        self.right = 'R'  # Red
        self.up = 'U'     # Blue
        self.down = 'D'   # Green
    
    def y_cw(self):
        """Rotate cube Y clockwise (F→R→B→L→F)."""
        self.front, self.right, self.back, self.left = \
            self.left, self.front, self.right, self.back
    
    def y_ccw(self):
        """Rotate cube Y counter-clockwise (F→L→B→R→F)."""
        self.front, self.left, self.back, self.right = \
            self.right, self.front, self.left, self.back
    
    def get_gripper_for_face(self, face):
        """Return which gripper currently controls this face (or None for F/B)."""
        if self.left == face:
            return 0
        elif self.up == face:
            return 2
        elif self.right == face:
            return 6
        elif self.down == face:
            return 8
        else:
            return None  # F or B position
    
    def is_standard(self):
        """Check if cube is in standard orientation."""
        return (self.front == 'F' and self.up == 'U')

# ─── Low-level servo control ────────────────────────────────────────────────

class CubeController:
    def __init__(self, port='/dev/ttyACM0'):
        self.ctrl = maestro.Controller(port)
        for ch in [0, 2, 6, 8]:
            self.ctrl.setAccel(ch, GRIPPER_ACCEL)
        self.move_count = 0
        self.orientation = Orientation()
    
    def close(self):
        self.ctrl.close()
    
    def _set_gripper(self, servo, pos_name):
        us = GRIPPER[servo][pos_name]
        self.ctrl.setTarget(servo, us * 4)
    
    def _set_rp(self, rp_servo, pos_name):
        us = RP[rp_servo][pos_name]
        self.ctrl.setTarget(rp_servo, us * 4)
    
    def _engage(self, gripper, slow=True):
        rp = GRIPPER_TO_RP[gripper]
        if slow:
            self.ctrl.setSpeed(rp, RP_SLOW_SPEED)
        self._set_rp(rp, "hold")
        if slow:
            time.sleep(RP_ENGAGE_DELAY)
            self.ctrl.setSpeed(rp, RP_NORMAL_SPEED)
    
    def _retract(self, gripper):
        rp = GRIPPER_TO_RP[gripper]
        self.ctrl.setSpeed(rp, RP_NORMAL_SPEED)
        self._set_rp(rp, "retracted")
    
    def _engage_simultaneous(self, *grippers, slow=True):
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

    # ─── Face Turn Primitive ─────────────────────────────────────────────

    def face_turn(self, gripper, direction):
        """
        Turn a face. All grippers start at B, all RP in hold.
        
        ALL servos follow the same pattern (verified 2026-03-06):
        - CW = B→C (A→B→C→D is clockwise from face perspective)
        - CCW = B→A (D→C→B→A is counter-clockwise)
        - 180° = B→D
        """
        target = {'cw': 'C', 'ccw': 'A', '180': 'D'}[direction]
        
        self.move_count += 1
        label = {0: 'L', 2: 'U', 6: 'R', 8: 'D'}[gripper]
        print(f"  [{self.move_count}] Face turn: {label} {direction}")
        
        # Gripper rotates, turning the face
        self._set_gripper(gripper, target)
        # 180° turns need more time to settle
        delay = TURN_DELAY_180 if direction == '180' else TURN_DELAY_90
        time.sleep(delay)
        
        # Reset gripper back to B
        self._retract(gripper)
        time.sleep(RP_DELAY)
        self._set_gripper(gripper, "B")
        time.sleep(MOVE_DELAY)
        # Extra settling time before re-engage after 180° turns
        if direction == '180':
            time.sleep(0.2)
        self._engage(gripper)
        time.sleep(RP_DELAY)

    # ─── Cube Rotation Primitive ─────────────────────────────────────────

    def cube_rotate_y(self, direction):
        """Rotate entire cube around Y axis (up-down)."""
        print(f"  [~] Cube rotation y {direction}")
        
        if direction == 'cw':
            s2_target, s8_target = 'A', 'C'
            self.orientation.y_cw()
        else:
            s2_target, s8_target = 'C', 'A'
            self.orientation.y_ccw()
        
        # Retract 0&6
        self._retract(0)
        self._retract(6)
        time.sleep(RP_DELAY)
        
        # Rotate cube
        self._set_gripper(2, s2_target)
        self._set_gripper(8, s8_target)
        time.sleep(ROTATE_DELAY)
        
        # Transfer hold
        self._engage_simultaneous(0, 6)
        time.sleep(0.5)
        self._retract(2)
        self._retract(8)
        time.sleep(RP_DELAY)
        
        # Reset 2&8 to B
        self._set_gripper(2, "B")
        self._set_gripper(8, "B")
        time.sleep(MOVE_DELAY)
        
        # Re-engage
        self._engage_simultaneous(2, 8)
        time.sleep(0.3)

    # ─── High-level Move Execution ───────────────────────────────────────

    def execute_move(self, move):
        """Execute a single Kociemba move with orientation tracking."""
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
        
        # Check which gripper currently controls this face
        gripper = self.orientation.get_gripper_for_face(face)
        
        if gripper is not None:
            # Direct face turn (no rotation needed)
            self.face_turn(gripper, direction)
        else:
            # F or B move - need to rotate cube
            if self.orientation.front == face:
                # F is at front - rotate so it goes to R
                self.cube_rotate_y('cw')
                self.face_turn(6, direction)
            elif self.orientation.back == face:
                # B is at back - rotate so it goes to R
                self.cube_rotate_y('ccw')
                self.face_turn(6, direction)
            # Don't rotate back yet - might be more F/B moves coming!

    def return_to_standard(self):
        """Return cube to standard orientation if needed."""
        if self.orientation.is_standard():
            print("  [✓] Already in standard orientation")
            return
        
        print("  [~] Returning to standard orientation...")
        # Simple approach: rotate until we're back
        attempts = 0
        while not self.orientation.is_standard() and attempts < 4:
            self.cube_rotate_y('cw')
            attempts += 1
        
        if not self.orientation.is_standard():
            print("  [!] WARNING: Could not return to standard orientation")

    def execute_solution(self, solution_string):
        """Execute a full Kociemba solution string."""
        moves = solution_string.strip().split()
        total = len(moves)
        
        print(f"\n═══ EXECUTING SOLUTION: {solution_string} ═══")
        print(f"    Total moves: {total}\n")
        
        # Setup: all grippers at B, all RP holding
        print("  Setting up: all grippers B, all RP hold")
        for g in [0, 2, 6, 8]:
            self._set_gripper(g, "B")
        time.sleep(MOVE_DELAY)
        self._engage_all()
        time.sleep(RP_DELAY)
        
        # Execute moves
        for i, move in enumerate(moves):
            print(f"\n── Move {i+1}/{total}: {move} ──")
            self.execute_move(move)
        
        # Return to standard orientation
        print("\n── Finalizing ──")
        self.return_to_standard()
        
        print(f"\n═══ SOLUTION COMPLETE ({self.move_count} servo moves) ═══")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="RCubed Move Executor v2 (with orientation tracking)")
    parser.add_argument('solution', nargs='?', help='Kociemba solution string')
    parser.add_argument('--test', action='store_true', help='Test single move')
    parser.add_argument('--move', type=str, help='Single move to test')
    parser.add_argument('--port', default='/dev/ttyACM0', help='Maestro port')
    args = parser.parse_args()
    
    cc = CubeController(args.port)
    
    try:
        if args.test and args.move:
            print(f"Testing single move: {args.move}")
            cc._engage_all()
            time.sleep(0.5)
            cc.execute_move(args.move)
            cc.return_to_standard()
        elif args.solution:
            cc.execute_solution(args.solution)
        else:
            print("Usage: python3 move_executor_v2.py 'R2 U F L2'")
            print("       python3 move_executor_v2.py --test --move F")
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted!")
    finally:
        cc.close()
        print("Done.")


if __name__ == "__main__":
    main()
