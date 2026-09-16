"""RCubed — Rubik's cube solving robot (RCR3D mechanics, Pololu Maestro, Raspberry Pi 5).

Layers, bottom to top:

    maestro      raw Pololu serial protocol
    backends     MaestroBackend (real) / SimBackend (no hardware)
    robot        servo primitives + collision guard + persisted state
    choreography face turns and whole-cube rotations built from primitives
    cube_model   54-facelet cube state, used both for tracking and for tests
    solver       Kociemba wrapper
    cli          `python -m rcubed ...`
"""

__version__ = "2.0.0-dev"
