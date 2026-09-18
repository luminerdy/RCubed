import random

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from rcubed.backends import SimBackend
from rcubed.camera import FakeCamera
from rcubed.choreography import Choreographer
from rcubed.config import RobotConfig
from rcubed.cube_model import CubeModel
from rcubed.robot import Robot
from rcubed.scanner import Scanner
from rcubed.vision import ColorModel, _assign, classify_scan, train


class NoisyFakeCamera(FakeCamera):
    """Adds per-pixel noise and a bright streak so cells are not perfectly flat."""

    def capture(self):
        frame = super().capture().astype(np.int16)
        rng = np.random.default_rng(self.captures)
        frame += rng.integers(-25, 26, frame.shape, dtype=np.int16)
        x1, y1, x2, y2 = self.box
        frame[y1:y2, x1 + (x2 - x1) // 3 : x1 + (x2 - x1) // 3 + 6] = 250  # glare stripe
        return np.clip(frame, 0, 255).astype(np.uint8)


@pytest.fixture
def cfg():
    return RobotConfig.load()


def make_rig(cfg, tmp_path, name):
    robot = Robot(SimBackend(), cfg, state_file=tmp_path / f"{name}.json")
    ch = Choreographer(robot, cfg)
    ch.safe_startup()
    ch.engage_all()
    cam = NoisyFakeCamera(lambda: ch.model.face("F"), cfg.camera)
    return ch, cam


def test_assignment_respects_capacity():
    cost = np.zeros((16, 2))
    cost[:, 1] = 1.0  # everyone prefers column 0
    out = _assign(cost, capacity=8)
    assert out.count(0) == 8 and out.count(1) == 8


def test_train_on_solved_then_read_scrambled(cfg, tmp_path):
    # training data: a solved cube plus two known scrambles, all self-labelled
    ch, cam = make_rig(cfg, tmp_path, "train")
    dirs = []
    for i, scr in enumerate(["", "R U F' L2 D", "B2 L' U2 R D' F"]):
        if scr:
            ch.execute(scr)
        d = tmp_path / f"scan{i}"
        Scanner(ch, cam, cfg).scan(d, known_state=True)
        dirs.append(d)
    model, report = train(dirs)
    assert report["scans"] == 3 and report["samples"] == 162
    assert report["training_errors"] == 0
    model.save(tmp_path / "colors.json")
    model = ColorModel.load(tmp_path / "colors.json")

    # a fresh, unknown cube: classify and compare with the truth
    random.seed(5)
    moves = [f + s for f in "URFDLB" for s in ("", "'", "2")]
    scr = " ".join(random.choice(moves) for _ in range(20))
    ch2, cam2 = make_rig(cfg, tmp_path, "test")
    ch2.execute(scr)
    truth = CubeModel().apply(scr)
    d = tmp_path / "unknown"
    Scanner(ch2, cam2, cfg).scan(d, known_state=False)
    result = classify_scan(d, model)
    assert result["facelets"] == truth.state
    assert "?" not in result["facelets"]
    assert CubeModel(result["facelets"]).kociemba_string() == truth.kociemba_string()
