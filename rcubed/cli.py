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
    python -m rcubed collect --count 10       scan, scramble, repeat: self-labelled training data
    python -m rcubed train                    fit the colour model from all labelled scans
    python -m rcubed read data/scans/<dir>    classify a scan and print the solution (no robot)
    python -m rcubed solve [--dry-run]        scan, classify, solve, execute

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


def labelled_scan_dirs() -> list[Path]:
    import json

    out = []
    for m in sorted((DATA_DIR / "scans").glob("*/manifest.json")):
        if json.loads(m.read_text()).get("known_state"):
            out.append(m.parent)
    return out


def cmd_train(args) -> int:
    from .vision import DEFAULT_MODEL, train

    dirs = [Path(d) for d in args.dirs] or labelled_scan_dirs()
    if not dirs:
        print("no labelled scans under data/scans (run `scan --known` or `collect`)")
        return 1
    model, report = train(dirs)
    out = Path(args.out) if args.out else DEFAULT_MODEL
    model.save(out)
    print(f"trained on {report['scans']} scans, {report['samples']} stickers, "
          f"{report['training_errors']} training errors -> {out}")
    return 0


def read_scan(scan_dir: Path, model_path: str | None) -> tuple[str, str | None]:
    """Classify a scan; return (facelets, solution or None). Prints a report."""
    from .cube_model import CubeModel
    from .solver import InvalidCubeError, solve
    from .vision import DEFAULT_MODEL, ColorModel, classify_scan

    model = ColorModel.load(Path(model_path) if model_path else DEFAULT_MODEL)
    result = classify_scan(scan_dir, model)
    for p in result["photos"]:
        print(f"  {p['file']:28s} {p['face']}  {p['unconstrained']}")
    print(f"  smallest margin {result['min_margin']:.2f}, "
          f"{result['changed_by_constraint']} stickers changed by the 8-per-colour rule")
    cube = CubeModel(result["facelets"])
    print(cube.pretty())
    if cube.is_solved:
        print("cube is already solved")
        return result["facelets"], ""
    try:
        solution = solve(cube)
    except InvalidCubeError as e:
        print(f"not a valid cube state: {e}")
        return result["facelets"], None
    print(f"solution ({len(solution.split())} moves): {solution}")
    return result["facelets"], solution


def cmd_read(args) -> int:
    _, solution = read_scan(Path(args.scan_dir), args.model)
    return 0 if solution is not None else 1


def cmd_collect(args, ch, scanner) -> int:
    """Scan a cube of known state, scramble it with tracked moves, repeat.

    Start with a *solved* cube loaded white front, blue top: that is the only
    way the model's state is known at the start. Every scan is then labelled by
    the model. If a colour model already exists, each scan is also read back
    and any disagreement is reported: that is how a slipped move shows up."""
    import random

    from .vision import DEFAULT_MODEL, ColorModel, classify_scan

    model = ColorModel.load(DEFAULT_MODEL) if DEFAULT_MODEL.exists() else None
    if not ch.model.is_solved:
        print("warning: the tracked cube state is not solved; labels assume the cube matches the model")
    moves = [f + s for f in "URFDLB" for s in ("", "'", "2")]
    for i in range(1, args.count + 1):
        out = DATA_DIR / "scans" / time.strftime("%Y%m%d-%H%M%S")
        scanner.scan(out, known_state=True)
        note = ""
        if model is not None:
            got = classify_scan(out, model)["facelets"]
            diff = sum(a != b for a, b in zip(got, ch.model.state))
            note = f"  read-back mismatches: {diff}" + ("  <-- check for a slipped move" if diff else "")
        print(f"[{i}/{args.count}] {out.name}{note}")
        if i < args.count:
            scr = []
            while len(scr) < args.moves:
                m = random.choice(moves)
                if scr and m[0] == scr[-1][0]:
                    continue  # no two moves on the same face in a row
                scr.append(m)
            ch.execute(" ".join(scr))
    return 0


def cmd_solve(args, ch, scanner) -> int:
    out = DATA_DIR / "scans" / time.strftime("%Y%m%d-%H%M%S")
    scanner.scan(out, known_state=False)
    facelets, solution = read_scan(out, args.model)
    if solution is None:
        print("cannot solve: fix the reading first (see the scan in", out, ")")
        return 1
    if solution == "":
        return 0
    if args.dry_run:
        print("dry run: not executing")
        return 0
    from .cube_model import CubeModel

    ch.model = CubeModel(facelets)  # the robot now knows the real state
    ch.execute(solution)
    print("solved" if ch.model.is_solved else "executed, but the tracked state is not solved")
    print(ch.status())
    return 0


def open_robot(args) -> tuple[Robot, Choreographer]:
    cfg = RobotConfig.load(args.config).scaled_timing(getattr(args, "timing_scale", 1.0))
    if getattr(args, "timing_scale", 1.0) != 1.0:
        print(f"timing scaled to {args.timing_scale:g}x: "
              + " ".join(f"{k}={cfg.t(k)}" for k in ("turn_90", "x_rotation", "rp_engage")))
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
    p.add_argument("--timing-scale", type=float, default=1.0, metavar="F",
                   help="multiply every wait by F for a tuning run (1.0 = config as written)")
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
    co = sub.add_parser("collect")
    co.add_argument("--count", type=int, default=10, help="number of scans")
    co.add_argument("--moves", type=int, default=8, help="scramble length between scans")
    tr = sub.add_parser("train")
    tr.add_argument("dirs", nargs="*", help="scan directories (default: all labelled under data/scans)")
    tr.add_argument("--out")
    rd = sub.add_parser("read")
    rd.add_argument("scan_dir")
    rd.add_argument("--model")
    so = sub.add_parser("solve")
    so.add_argument("--dry-run", action="store_true", help="scan and solve but do not execute")
    so.add_argument("--model")

    args = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")

    if args.cmd == "snapshot":
        return cmd_snapshot(args)
    if args.cmd == "train":
        return cmd_train(args)
    if args.cmd == "read":
        return cmd_read(args)

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
        elif args.cmd in ("scan", "collect", "solve"):
            from .scanner import Scanner

            if args.sim:
                from .camera import FakeCamera

                camera = FakeCamera(lambda: ch.model.face("F"), robot.cfg.camera)
            else:
                from .camera import Camera

                camera = Camera(robot.cfg.camera)
            scanner = Scanner(ch, camera, robot.cfg)
            ch.ensure_known()
            try:
                if args.cmd == "scan":
                    out = Path(args.out) if args.out else DATA_DIR / "scans" / time.strftime("%Y%m%d-%H%M%S")
                    manifest = scanner.scan(out, known_state=args.known, home=not args.no_home)
                    print(f"{len(manifest['photos'])} photos -> {out}")
                    for ph in manifest["photos"]:
                        print(f"  {ph['file']:28s} {ph['color']:7s} {ph['stickers']}")
                    print(ch.status())
                elif args.cmd == "collect":
                    return cmd_collect(args, ch, scanner)
                else:
                    return cmd_solve(args, ch, scanner)
            finally:
                camera.close()
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
