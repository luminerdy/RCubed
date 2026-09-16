#!/usr/bin/env python3
"""
RCubed - Reset to Starting Position
Sets all servos to the calibrated starting position:
- TURN servos (0,2,6,8): Claw A
- MOVE servos (1,3,7,9): Retracted

Note: Maestro Control Center shows values in microseconds (μs),
but the maestro.py library expects quarter-microseconds (×4).
"""

import maestro
import time

servo = maestro.Controller()

print('Resetting all servos to starting position...')
print()

# TURN servos to Claw A (microseconds × 4 = quarter-microseconds)
print('TURN servos → Claw A:')
servo.setTarget(0, 1232 * 4)  # 4928
servo.setTarget(2, 1168 * 4)  # 4672
servo.setTarget(6, 1315 * 4)  # 5260
servo.setTarget(8, 1315 * 4)  # 5260
print('  Ch 0: 1232 μs (4928 qμs)')
print('  Ch 2: 1168 μs (4672 qμs)')
print('  Ch 6: 1315 μs (5260 qμs)')
print('  Ch 8: 1315 μs (5260 qμs)')

time.sleep(1)

# MOVE servos to Retracted (microseconds × 4 = quarter-microseconds)
print()
print('MOVE servos → Retracted:')
servo.setTarget(1, 1848 * 4)  # 7392
servo.setTarget(3, 1814 * 4)  # 7256
servo.setTarget(7, 1657 * 4)  # 6628
servo.setTarget(9, 1892 * 4)  # 7568
print('  Ch 1: 1848 μs (7392 qμs)')
print('  Ch 3: 1814 μs (7256 qμs)')
print('  Ch 7: 1657 μs (6628 qμs)')
print('  Ch 9: 1892 μs (7568 qμs)')

time.sleep(2)

print()
print('✅ All servos at starting position!')

servo.close()
