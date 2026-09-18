"""Command-line entry point: `python -m rcubed <command>`.

    python -m rcubed status                   show remembered servo state
    python -m rcubed safe-start               reset to all-B / released from unknown state
    python -m rcubed load                     fingers clear, ready to insert a cube
    python -m rcubed grip | release           engage / retract all four RPs
    python -m rcubed move "R U R' U'"         execute moves (standard notation)
    python -m rcubed retract                  EMERGENCY: release everything, forget state
    python -m rcubed servo 6 1500             raw pulse width (calibration only)
    python -m rcubed snapshot                 photo with the crop grid drawn (no servo motion)
    python -m rcubed scan [--known]           photograph all six faces into data/scans/<time>/

    --sim        run against the simulator instead of the Maestro (prints a trace)
    --realtime   make the simulator sleep for real
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from .backends import MaestroBackend, SimBackend
from .choreography import Choreographer
from .config import REPO_ROOT, RobotConfig
from .robot import Robot

DATA_DIR = REPO_ROOT / "data"


def cmd_snapshot(args) -> int:
    """Grab one frame, save it raw and with the crop grid drawn. No robot needed."""
    import cv2

    from .camera import Camera, crop, draw_grid

    cfg = RobotConfig.load(args.config)
    out_dir = Path(args.out) if args.out else DATA_DIR / "snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    cam = Camera(cfg.camera).open()
    try:
        frame = cam.capture()
    finally:
        cam.close()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    box = cam.box
    cv2.imwrite(str(out_dir / f"{stamp}_full.jpg"), frame)
    cv2.imwrite(str(out_dir / f"{stamp}_grid.jpg"), draw_grid(frame, box))
    cv2.imwrite(str(out_dir / f"{stamp}_face.jpg"), crop(frame, box))
    print(f"camera {cam.width}x{cam.height}, crop box {box}")
    print(f"saved {out_dir / (stamp + '_grid.jpg')}")
    return 0


def open_robot(args) -> tuple[Robot, Choreographer]:
    cfg = RobotConfig.load(args.config)
    if args.sim:
        backend = SimBackend(realtime=args.realtime, echo=args.verbose)
        robot = Robot(backend, cfg, state_file=None)  # never touch the real state file
    else:
        backend = MaestroBackend(args.port)
        print(f"Maestro on {backend.port}")
        robot = Robot(backend, cfg)
        if robot.load_state():
            print("state restored:", robot.describe())
    return robot, Choreographer(robot, cfg)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="rcubed", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sim", action="store_true", help="simulate instead of driving the Maestro")
    p.add_argument("--realtime", action="store_true", help="simulator sleeps for real")
    p.add_argument("--port", help="Maestro command port (default: auto-detect)")
    p.add_argument("--config", help="path to robot.json")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    sub.add_parser("safe-start")
    sub.add_parser("load")
    sub.add_parser("grip")
    sub.add_parser("release")
    sub.add_parser("retract")
    m = sub.add_parser("move")
    m.add_argument("moves", nargs="+")
    m.add_argument("--no-home", action="store_true", help="leave the cube in whatever orientation it ends in")
    s = sub.add_parser("servo")
    s.add_argument("channel", type=int)
    s.add_argument("us", type=int)
    sn = sub.add_parser("snapshot")
    sn.add_argument("--out", help="directory (default data/snapshots)")
    sc = sub.add_parser("scan")
    sc.add_argument("--out", help="directory (default data/scans/<timestamp>)")
    sc.add_argument("--known", action="store_true", help="the cube state is known (labels are trustworthy)")
    sc.add_argument("--no-home", action="store_true")

    args = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")

    if args.cmd == "snapshot":
        return cmd_snapshot(args)

    robot, ch = open_robot(args)
    try:
        if args.cmd == "status":
            print(ch.status())
        elif args.cmd == "safe-start":
            ch.safe_startup()
            print(robot.describe())
        elif args.cmd == "load":
            ch.load_position()
            print("ready to load: white front, blue top")
            print(robot.describe())
        elif args.cmd == "grip":
            ch.ensure_known()
            ch.engage_all()
        elif args.cmd == "release":
            ch.ensure_known()
            ch.release_all()
        elif args.cmd == "retract":
            for g in (0, 2, 6, 8):
                robot.set_rp(robot.cfg.rp_of(g), "retracted", speed=0)
            robot.settle(robot.cfg.t("rp_retract"))
            robot.invalidate_state()
            robot.gripper = {g: None for g in robot.gripper}
            print("all RPs retracted; state invalidated (next run does safe startup)")
        elif args.cmd == "move":
            ch.ensure_known()
            ch.execute(" ".join(args.moves), home=not args.no_home)
            print(ch.status())
            if args.sim:
                print(f"simulated time: {robot.backend.clock:.1f}s")
        elif args.cmd == "servo":
            robot.set_raw(args.channel, args.us)
            robot.invalidate_state()
            print(f"channel {args.channel} -> {args.us} us (state invalidated)")
        elif args.cmd == "scan":
            from .scanner import Scanner

            if args.sim:
                from .camera import FakeCamera

                camera = FakeCamera(lambda: ch.model.face("F"), robot.cfg.camera)
            else:
                from .camera import Camera

                camera = Camera(robot.cfg.camera)
            out = Path(args.out) if args.out else DATA_DIR / "scans" / time.strftime("%Y%m%d-%H%M%S")
            ch.ensure_known()
            try:
                manifest = Scanner(ch, camera, robot.cfg).scan(out, known_state=args.known, home=not args.no_home)
            finally:
                camera.close()
            print(f"{len(manifest['photos'])} photos -> {out}")
            for ph in manifest["photos"]:
                print(f"  {ph['file']:28s} {ph['color']:7s} {ph['stickers']}")
            print(ch.status())
    except KeyboardInterrupt:
        print("\ninterrupted — retracting all RPs", file=sys.stderr)
        for g in (0, 2, 6, 8):
            robot.set_rp(robot.cfg.rp_of(g), "retracted", speed=0)
        robot.invalidate_state()
        return 130
    except Exception:
        robot.invalidate_state()
        raise
    finally:
        robot.close()
    return 0
