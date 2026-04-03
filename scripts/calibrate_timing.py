#!/usr/bin/env python3
"""
RCubed Timing Calibration Script
================================

Measures actual servo movement times to optimize the TIMING config.
Uses Maestro position feedback to detect when servos have settled.

Usage:
    python3 scripts/calibrate_timing.py           # Full calibration
    python3 scripts/calibrate_timing.py --quick   # Just key moves
    python3 scripts/calibrate_timing.py --servo 6 # Single servo

Output:
    Recommended TIMING values for cube_controller.py

Author: RubikPi + Scotty
Date: 2026-04-03
"""

import sys
import os
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import maestro

# ─── Config (from cube_controller.py) ───────────────────────────────────────

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
X_SPEED = {0: 60, 6: 45}

# Settling threshold (quarter-microseconds)
SETTLE_THRESHOLD = 40  # ~10μs tolerance

# ─── Helpers ────────────────────────────────────────────────────────────────

class TimingCalibrator:
    def __init__(self, port='/dev/ttyACM0'):
        self.ctrl = maestro.Controller(port)
        self.results = {}
        
        # Set acceleration
        for ch in [0, 2, 6, 8]:
            self.ctrl.setAccel(ch, 110)
    
    def close(self):
        self.ctrl.close()
    
    def _set_servo(self, ch, us, speed=0):
        """Set servo position in microseconds."""
        self.ctrl.setSpeed(ch, speed)
        self.ctrl.setTarget(ch, us * 4)
    
    def _get_position(self, ch):
        """Get current servo position in quarter-microseconds."""
        return self.ctrl.getPosition(ch)
    
    def _wait_settled(self, ch, target_us, timeout=5.0):
        """
        Wait for servo to reach target position.
        Returns actual time taken.
        """
        target_qus = target_us * 4
        start = time.time()
        
        while time.time() - start < timeout:
            pos = self._get_position(ch)
            if abs(pos - target_qus) < SETTLE_THRESHOLD:
                return time.time() - start
            time.sleep(0.02)  # 20ms poll interval
        
        # Timeout - servo didn't reach target
        return -1
    
    def _measure_move(self, ch, from_us, to_us, speed=0, trials=3):
        """
        Measure time for a servo move, averaged over trials.
        """
        times = []
        
        for _ in range(trials):
            # Go to start position and wait
            self._set_servo(ch, from_us, speed=0)
            time.sleep(0.5)
            
            # Measure move to target
            self._set_servo(ch, to_us, speed=speed)
            elapsed = self._wait_settled(ch, to_us)
            
            if elapsed > 0:
                times.append(elapsed)
            else:
                print(f"  ⚠️  Timeout on servo {ch}")
        
        if times:
            return sum(times) / len(times)
        return -1
    
    # ─── Calibration Routines ───────────────────────────────────────────
    
    def calibrate_gripper_moves(self, servo):
        """Calibrate gripper servo movements (90° and 180°)."""
        print(f"\n═══ GRIPPER {servo} ═══")
        cal = GRIPPER_CAL[servo]
        
        # 90° moves (B→C, B→A)
        print(f"  B→C (90° CW)...", end=" ", flush=True)
        t_bc = self._measure_move(servo, cal['B'], cal['C'])
        print(f"{t_bc:.3f}s")
        
        print(f"  C→B (90° reset)...", end=" ", flush=True)
        t_cb = self._measure_move(servo, cal['C'], cal['B'])
        print(f"{t_cb:.3f}s")
        
        print(f"  B→A (90° CCW)...", end=" ", flush=True)
        t_ba = self._measure_move(servo, cal['B'], cal['A'])
        print(f"{t_ba:.3f}s")
        
        print(f"  A→B (90° reset)...", end=" ", flush=True)
        t_ab = self._measure_move(servo, cal['A'], cal['B'])
        print(f"{t_ab:.3f}s")
        
        # 180° move (B→D)
        print(f"  B→D (180°)...", end=" ", flush=True)
        t_bd = self._measure_move(servo, cal['B'], cal['D'])
        print(f"{t_bd:.3f}s")
        
        print(f"  D→B (180° reset)...", end=" ", flush=True)
        t_db = self._measure_move(servo, cal['D'], cal['B'])
        print(f"{t_db:.3f}s")
        
        avg_90 = (t_bc + t_cb + t_ba + t_ab) / 4
        avg_180 = (t_bd + t_db) / 2
        
        self.results[f'gripper_{servo}_90'] = avg_90
        self.results[f'gripper_{servo}_180'] = avg_180
        
        print(f"  Average 90°: {avg_90:.3f}s")
        print(f"  Average 180°: {avg_180:.3f}s")
        
        return avg_90, avg_180
    
    def calibrate_rp_moves(self, rp):
        """Calibrate rack-and-pinion servo movements."""
        print(f"\n═══ RP {rp} ═══")
        cal = RP_CAL[rp]
        
        # Fast retract
        print(f"  hold→retracted (fast)...", end=" ", flush=True)
        self._set_servo(rp, cal['hold'])
        time.sleep(0.5)
        t_retract = self._measure_move(rp, cal['hold'], cal['retracted'], speed=0)
        print(f"{t_retract:.3f}s")
        
        # Slow engage
        print(f"  retracted→hold (slow, speed=30)...", end=" ", flush=True)
        t_engage = self._measure_move(rp, cal['retracted'], cal['hold'], speed=30)
        print(f"{t_engage:.3f}s")
        
        self.results[f'rp_{rp}_retract'] = t_retract
        self.results[f'rp_{rp}_engage'] = t_engage
        
        return t_retract, t_engage
    
    def calibrate_x_rotation(self):
        """Calibrate X rotation (synchronized 0 & 6)."""
        print(f"\n═══ X ROTATION ═══")
        
        # Setup: both at B
        self._set_servo(0, GRIPPER_CAL[0]['B'])
        self._set_servo(6, GRIPPER_CAL[6]['B'])
        time.sleep(0.5)
        
        # X forward: 0:B→C, 6:B→A with synchronized speeds
        print(f"  X forward (0:B→C, 6:B→A)...", end=" ", flush=True)
        
        self.ctrl.setSpeed(0, X_SPEED[0])
        self.ctrl.setSpeed(6, X_SPEED[6])
        
        start = time.time()
        self._set_servo(0, GRIPPER_CAL[0]['C'], speed=X_SPEED[0])
        self._set_servo(6, GRIPPER_CAL[6]['A'], speed=X_SPEED[6])
        
        # Wait for both to settle
        t0 = self._wait_settled(0, GRIPPER_CAL[0]['C'])
        t6 = self._wait_settled(6, GRIPPER_CAL[6]['A'])
        
        t_x = max(t0, t6) if t0 > 0 and t6 > 0 else -1
        print(f"{t_x:.3f}s (servo 0: {t0:.3f}s, servo 6: {t6:.3f}s)")
        
        self.ctrl.setSpeed(0, 0)
        self.ctrl.setSpeed(6, 0)
        
        self.results['x_rotation'] = t_x
        return t_x
    
    def calibrate_y_rotation(self):
        """Calibrate Y rotation (synchronized 2 & 8)."""
        print(f"\n═══ Y ROTATION ═══")
        
        # Setup: both at B
        self._set_servo(2, GRIPPER_CAL[2]['B'])
        self._set_servo(8, GRIPPER_CAL[8]['B'])
        time.sleep(0.5)
        
        # Y: 2:B→C, 8:B→A
        print(f"  Y (2:B→C, 8:B→A)...", end=" ", flush=True)
        
        start = time.time()
        self._set_servo(2, GRIPPER_CAL[2]['C'])
        self._set_servo(8, GRIPPER_CAL[8]['A'])
        
        t2 = self._wait_settled(2, GRIPPER_CAL[2]['C'])
        t8 = self._wait_settled(8, GRIPPER_CAL[8]['A'])
        
        t_y = max(t2, t8) if t2 > 0 and t8 > 0 else -1
        print(f"{t_y:.3f}s (servo 2: {t2:.3f}s, servo 8: {t8:.3f}s)")
        
        self.results['y_rotation'] = t_y
        return t_y
    
    def run_full_calibration(self):
        """Run complete calibration."""
        print("╔════════════════════════════════════════╗")
        print("║     RCubed Timing Calibration          ║")
        print("╚════════════════════════════════════════╝")
        print("\nThis will move servos to measure actual timing.")
        print("Make sure cube is NOT loaded.\n")
        input("Press Enter to start...")
        
        # Gripper servos
        for servo in [0, 2, 6, 8]:
            self.calibrate_gripper_moves(servo)
        
        # RP servos
        for rp in [1, 3, 7, 9]:
            self.calibrate_rp_moves(rp)
        
        # Rotations
        self.calibrate_x_rotation()
        self.calibrate_y_rotation()
        
        # Generate recommendations
        self.print_recommendations()
    
    def run_quick_calibration(self):
        """Quick calibration - just key timings."""
        print("╔════════════════════════════════════════╗")
        print("║     Quick Timing Calibration           ║")
        print("╚════════════════════════════════════════╝")
        print("\nTesting key moves only.\n")
        input("Press Enter to start...")
        
        # Just one gripper and one RP
        self.calibrate_gripper_moves(6)  # R gripper (most used)
        self.calibrate_rp_moves(7)       # R gripper's RP
        self.calibrate_x_rotation()
        self.calibrate_y_rotation()
        
        self.print_recommendations()
    
    def print_recommendations(self):
        """Print recommended TIMING values."""
        print("\n" + "═" * 50)
        print("RECOMMENDED TIMING VALUES")
        print("═" * 50)
        
        # Calculate with 20% safety margin
        margin = 1.2
        
        # Gripper moves
        grip_90_times = [v for k, v in self.results.items() if 'gripper' in k and '90' in k and v > 0]
        grip_180_times = [v for k, v in self.results.items() if 'gripper' in k and '180' in k and v > 0]
        
        if grip_90_times:
            t90 = max(grip_90_times) * margin
            print(f"  'turn_90': {t90:.2f},      # was 1.2")
        
        if grip_180_times:
            t180 = max(grip_180_times) * margin
            print(f"  'turn_180': {t180:.2f},     # was 2.0")
        
        # RP moves
        rp_retract = [v for k, v in self.results.items() if 'retract' in k and v > 0]
        rp_engage = [v for k, v in self.results.items() if 'engage' in k and v > 0]
        
        if rp_retract:
            t_ret = max(rp_retract) * margin
            print(f"  'rp_retract': {t_ret:.2f},   # was 2.0")
        
        if rp_engage:
            t_eng = max(rp_engage) * margin
            print(f"  'rp_engage': {t_eng:.2f},    # was 2.0")
        
        # Rotations
        if 'x_rotation' in self.results and self.results['x_rotation'] > 0:
            t_x = self.results['x_rotation'] * margin
            print(f"  'x_rotation': {t_x:.2f},   # was 2.5")
        
        if 'y_rotation' in self.results and self.results['y_rotation'] > 0:
            t_y = self.results['y_rotation'] * margin
            print(f"  'y_rotation': {t_y:.2f},   # was 2.0")
        
        # Gripper reset (same as 90°)
        if grip_90_times:
            t_move = max(grip_90_times) * margin
            print(f"  'gripper_move': {t_move:.2f},  # was 0.8")
        
        print("\n" + "═" * 50)
        print("Copy these values to cube_controller.py TIMING dict")
        print("═" * 50)
        
        # Return home
        print("\nReturning servos to neutral...")
        for servo in [0, 2, 6, 8]:
            self._set_servo(servo, GRIPPER_CAL[servo]['B'])
        for rp in [1, 3, 7, 9]:
            self._set_servo(rp, RP_CAL[rp]['retracted'])
        time.sleep(1)


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="RCubed Timing Calibration")
    parser.add_argument('--quick', action='store_true', help='Quick calibration (key moves only)')
    parser.add_argument('--servo', type=int, help='Calibrate single servo')
    parser.add_argument('--port', default='/dev/ttyACM0')
    args = parser.parse_args()
    
    cal = TimingCalibrator(args.port)
    
    try:
        if args.servo is not None:
            if args.servo in [0, 2, 6, 8]:
                cal.calibrate_gripper_moves(args.servo)
            elif args.servo in [1, 3, 7, 9]:
                cal.calibrate_rp_moves(args.servo)
            cal.print_recommendations()
        elif args.quick:
            cal.run_quick_calibration()
        else:
            cal.run_full_calibration()
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
    finally:
        cal.close()


if __name__ == '__main__':
    main()
