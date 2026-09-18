"""Photograph all six faces.

The scan is a list of steps from `config/robot.json → scan.sequence`: "photo" takes a
picture of whatever face is at the front, anything else is a whole-cube rotation
token. Because the cube model is physical-frame, the model's F face at the moment
of each photo *is* the expected sticker layout of that image, top-left to
bottom-right — no per-face rotation corrections are needed.

Each scan writes one JPEG per photo (per lighting state) plus `manifest.json`:

    photos[i].file       image file name
    photos[i].face       which logical face the image shows (its centre colour)
    photos[i].stickers   the 9 expected stickers if the cube state was known
    photos[i].facelets   the 9 home-frame facelet indices (0-53) the cells show
    photos[i].lighting   lighting state name
    known_state          whether `stickers` can be trusted as labels
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from .camera import crop_box
from .choreography import Choreographer
from .config import RobotConfig
from .cube_model import FACES, CubeModel
from .lights import NullLights

log = logging.getLogger("rcubed.scan")

# Front from the load pose, half spin for the back, tumble for top and bottom,
# spin for the two sides. Six photos, six rotations.
DEFAULT_SEQUENCE = ["photo", "y2", "photo", "x'", "photo", "x2", "photo", "y", "photo", "y2", "photo"]


class OccludedError(RuntimeError):
    """A claw would be in the camera's view of the face."""

COLOR_NAMES = {"U": "blue", "R": "red", "F": "white", "D": "green", "L": "orange", "B": "yellow"}


def faces_covered(sequence: list[str], start: CubeModel | None = None) -> list[str]:
    """Which faces a sequence photographs, in order (model-only, no hardware)."""
    m = (start or CubeModel()).copy()
    seen = []
    for step in sequence:
        if step == "photo":
            seen.append(m.center("F"))
        else:
            m.apply(step)
    return seen


class Scanner:
    def __init__(self, choreo: Choreographer, camera, cfg: RobotConfig, lights=None):
        self.choreo = choreo
        self.camera = camera
        self.cfg = cfg
        self.lights = lights or NullLights()
        scan_cfg = cfg.raw.get("scan", {})
        self.sequence: list[str] = list(scan_cfg.get("sequence", DEFAULT_SEQUENCE))
        self.lighting: list[str] = list(scan_cfg.get("lighting", ["default"]))
        covered = faces_covered(self.sequence, self.choreo.model)
        if sorted(set(covered)) != sorted(FACES):
            raise ValueError(f"scan sequence covers {covered}, not all six faces")

    def _check_view_clear(self) -> None:
        """An engaged claw parked at B or D covers the middle sticker of its edge.
        Only claws at A or C (or retracted ones) leave the face fully visible."""
        robot = self.choreo.robot
        blocking = [g for g in robot.holding() if robot.gripper[g] not in ("A", "C")]
        if blocking:
            raise OccludedError(f"grippers {blocking} are engaged at B/D and would hide stickers")

    def scan(self, out_dir: Path, known_state: bool = False, home: bool = True) -> dict:
        import cv2

        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        self.camera.open()
        box = crop_box(self.cfg.camera, self.camera.width, self.camera.height)

        self.choreo.engage_all()
        self.choreo.go_home()  # the scan's home frame is the cube's orientation now
        if self.sequence and self.sequence[0] == "photo":
            self.choreo.park_for_photo("y")  # fingers 2/8 out of view before the first shot
        # A model whose 54 stickers are unique ids tracks which home facelet each
        # camera cell shows after the rotations, so photos map straight into a
        # 54-facelet string.
        ids = CubeModel("".join(chr(65 + i) for i in range(54)))
        photos = []
        n = 0
        t0 = time.time()
        for step in self.sequence:
            if step != "photo":
                self.choreo.rotate(step)
                ids.apply(step)
                continue
            n += 1
            self._check_view_clear()
            model = self.choreo.model
            face = model.center("F")
            facelets = [ord(c) - 65 for c in ids.face("F")]
            log.info("photo %d: %s face (%s)", n, face, COLOR_NAMES[face])
            for state in self.lighting:
                self.lights.set(state)
                frame = self.camera.capture()
                fname = f"face_{n}_{face}_{state}.jpg"
                cv2.imwrite(str(out_dir / fname), frame)
                photos.append(
                    {
                        "file": fname,
                        "index": n,
                        "face": face,
                        "color": COLOR_NAMES[face],
                        "stickers": model.face("F"),
                        "facelets": facelets,
                        "lighting": state,
                        "model": model.state,
                    }
                )
            self.lights.off()

        if home:
            self.choreo.go_home()
            self.choreo.prepare_for_turn()
        self.choreo.robot.save_state()

        manifest = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "duration_s": round(time.time() - t0, 1),
            "known_state": known_state,
            "camera": {"width": self.camera.width, "height": self.camera.height, "crop": list(box)},
            "sequence": self.sequence,
            "lighting": self.lighting,
            "color_names": COLOR_NAMES,
            "faces": [p["face"] for p in photos if p["lighting"] == self.lighting[0]],
            "photos": photos,
        }
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        log.info("scan complete: %d photos in %s", len(photos), out_dir)
        return manifest
