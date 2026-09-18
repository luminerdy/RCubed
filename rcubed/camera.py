"""Camera capture with locked settings, plus a fake camera for tests.

The crop box is defined in `config/robot.json` against a reference frame size and
scaled to whatever resolution the camera actually delivers, so the same numbers
work at 640x480 and 1280x960.
"""
from __future__ import annotations

import time
from typing import Callable

import numpy as np

Box = tuple[int, int, int, int]  # x1, y1, x2, y2


def crop_box(cam_cfg: dict, width: int, height: int) -> Box:
    rw, rh = cam_cfg.get("crop_ref", [640, 480])
    x1, y1, x2, y2 = cam_cfg["crop"]
    sx, sy = width / rw, height / rh
    return int(x1 * sx), int(y1 * sy), int(x2 * sx), int(y2 * sy)


def crop(frame: np.ndarray, box: Box) -> np.ndarray:
    x1, y1, x2, y2 = box
    return frame[y1:y2, x1:x2]


def cell_boxes(box: Box) -> list[Box]:
    """The nine sticker cells of a face crop, reading order, in frame coordinates."""
    x1, y1, x2, y2 = box
    cw, ch = (x2 - x1) / 3, (y2 - y1) / 3
    return [
        (int(x1 + c * cw), int(y1 + r * ch), int(x1 + (c + 1) * cw), int(y1 + (r + 1) * ch))
        for r in range(3)
        for c in range(3)
    ]


def draw_grid(frame: np.ndarray, box: Box) -> np.ndarray:
    """Copy of the frame with the crop box and 3x3 grid drawn on it."""
    import cv2

    out = frame.copy()
    x1, y1, x2, y2 = box
    cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
    for cx1, cy1, cx2, cy2 in cell_boxes(box):
        cv2.rectangle(out, (cx1, cy1), (cx2, cy2), (0, 200, 255), 1)
    return out


class Camera:
    """USB webcam via OpenCV. Warms up with auto exposure/white balance, then locks them."""

    def __init__(self, cam_cfg: dict):
        self.cfg = cam_cfg
        self.cap = None
        self.width = 0
        self.height = 0

    def open(self) -> "Camera":
        import cv2

        cap = cv2.VideoCapture(int(self.cfg.get("index", 0)))
        if not cap.isOpened():
            raise RuntimeError(f"cannot open camera index {self.cfg.get('index', 0)}")
        # The driver keeps a queue of frames. While the robot rotates for two seconds
        # the queue fills with frames of the *old* face and then stops, so without
        # draining it the next read returns a stale frame. Ask for the smallest
        # queue (honoured by V4L2) and drain by time in capture().
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        fourcc = self.cfg.get("fourcc")
        if fourcc:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.cfg.get("width", 640)))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.cfg.get("height", 480)))

        for _ in range(int(self.cfg.get("warmup_frames", 10))):
            cap.read()
            time.sleep(0.05)

        if self.cfg.get("lock_auto", True):
            cap.set(cv2.CAP_PROP_AUTO_WB, 0)
            if self.cfg.get("wb_temperature") is not None:
                cap.set(cv2.CAP_PROP_WB_TEMPERATURE, float(self.cfg["wb_temperature"]))
            if self.cfg.get("exposure") is not None:
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # manual mode on V4L2
                cap.set(cv2.CAP_PROP_EXPOSURE, float(self.cfg["exposure"]))
            for _ in range(3):
                cap.read()

        self.cap = cap
        self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return self

    def capture(self) -> np.ndarray:
        if self.cap is None:
            self.open()
        # Drain stale frames: keep grabbing for `flush_seconds` (at 30 fps that is
        # many more frames than any driver queue holds), then read a live one.
        deadline = time.monotonic() + float(self.cfg.get("flush_seconds", 0.5))
        grabbed = 0
        while time.monotonic() < deadline or grabbed < int(self.cfg.get("flush_frames", 8)):
            self.cap.grab()
            grabbed += 1
            if grabbed > 200:
                break
        ok, frame = self.cap.read()
        if not ok or frame is None:
            raise RuntimeError("camera read failed")
        return frame

    @property
    def box(self) -> Box:
        return crop_box(self.cfg, self.width, self.height)

    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None


class FakeCamera:
    """Renders whatever nine stickers `face_provider()` returns as flat colour patches,
    so the scanner can be tested without a camera or a robot."""

    COLORS = {  # BGR, deliberately far apart
        "U": (200, 80, 20),
        "R": (30, 30, 200),
        "F": (240, 240, 240),
        "D": (40, 180, 40),
        "L": (20, 120, 240),
        "B": (30, 220, 230),
    }

    def __init__(self, face_provider: Callable[[], str], cam_cfg: dict):
        self.face_provider = face_provider
        self.cfg = cam_cfg
        self.width = int(cam_cfg.get("width", 640))
        self.height = int(cam_cfg.get("height", 480))
        self.captures = 0

    def open(self) -> "FakeCamera":
        return self

    @property
    def box(self) -> Box:
        return crop_box(self.cfg, self.width, self.height)

    def capture(self) -> np.ndarray:
        frame = np.full((self.height, self.width, 3), 60, dtype=np.uint8)
        stickers = self.face_provider()
        for (x1, y1, x2, y2), s in zip(cell_boxes(self.box), stickers):
            pad = max(2, (x2 - x1) // 12)  # dark "sticker border" like a real cube
            frame[y1 + pad : y2 - pad, x1 + pad : x2 - pad] = self.COLORS[s]
        self.captures += 1
        return frame

    @classmethod
    def classify(cls, bgr) -> str:
        """Nearest fake colour, for tests that read the rendered images back."""
        return min(cls.COLORS, key=lambda k: sum((a - b) ** 2 for a, b in zip(cls.COLORS[k], bgr)))

    def close(self) -> None:
        pass
