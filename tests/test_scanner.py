import json

import pytest

cv2 = pytest.importorskip("cv2")

from rcubed.backends import SimBackend
from rcubed.camera import FakeCamera, cell_boxes, crop_box
from rcubed.choreography import Choreographer
from rcubed.config import GRIPPERS, RobotConfig
from rcubed.cube_model import FACES, CubeModel
from rcubed.robot import Robot
from rcubed.scanner import DEFAULT_SEQUENCE, Scanner, faces_covered


@pytest.fixture
def cfg():
    return RobotConfig.load()


@pytest.fixture
def rig(cfg, tmp_path):
    robot = Robot(SimBackend(), cfg, state_file=tmp_path / "state.json")
    ch = Choreographer(robot, cfg)
    ch.safe_startup()
    ch.engage_all()
    cam = FakeCamera(lambda: ch.model.face("F"), cfg.camera)
    return robot, ch, cam


def read_back(path, box):
    """Read the 9 sticker letters out of a rendered image, the way a detector would."""
    img = cv2.imread(str(path))
    out = ""
    for x1, y1, x2, y2 in cell_boxes(box):
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        patch = img[cy - 3 : cy + 4, cx - 3 : cx + 4].reshape(-1, 3).mean(axis=0)
        out += FakeCamera.classify(patch)
    return out


def test_default_sequence_covers_all_six_faces():
    assert sorted(faces_covered(DEFAULT_SEQUENCE)) == sorted(FACES)


def test_crop_box_scales_with_resolution(cfg):
    assert crop_box(cfg.camera, 640, 480) == tuple(cfg.camera["crop"])
    x1, y1, x2, y2 = crop_box(cfg.camera, 1280, 960)
    assert (x1, y1, x2, y2) == tuple(v * 2 for v in cfg.camera["crop"])


def test_scan_solved_cube(rig, cfg, tmp_path):
    robot, ch, cam = rig
    out = tmp_path / "scan"
    manifest = Scanner(ch, cam, cfg).scan(out, known_state=True)

    assert sorted(manifest["faces"]) == sorted(FACES)
    assert len(manifest["photos"]) == 6
    assert (out / "manifest.json").exists()
    box = tuple(manifest["camera"]["crop"])
    for p in manifest["photos"]:
        assert p["stickers"] == p["face"] * 9  # solved: every sticker matches the centre
        assert read_back(out / p["file"], box) == p["stickers"]
    # robot ends home, fingers at B, all holding
    assert ch.model.is_home
    assert all(robot.gripper[g] == "B" for g in GRIPPERS)
    assert len(robot.holding()) == 4


def test_scan_scrambled_cube_labels_match_images(rig, cfg, tmp_path):
    robot, ch, cam = rig
    scramble = "R U F' L2 D B' U2 R' F D2"
    ch.execute(scramble)
    manifest = Scanner(ch, cam, cfg).scan(tmp_path / "scan", known_state=True)
    box = tuple(manifest["camera"]["crop"])
    expected = CubeModel().apply(scramble)
    seen = set()
    for p in manifest["photos"]:
        assert read_back(tmp_path / "scan" / p["file"], box) == p["stickers"]
        # the camera sees the face rotated by the scan choreography; the manifest's
        # facelet map says which home facelet each cell shows
        assert [expected.state[i] for i in p["facelets"]] == list(p["stickers"])
        assert p["stickers"] in rotations_of(expected.face(p["face"]))
        seen.update(p["facelets"])
    assert seen == set(range(54))  # every facelet photographed exactly once
    assert ch.model == expected


def rotations_of(face9: str) -> set[str]:
    g = [list(face9[i * 3 : i * 3 + 3]) for i in range(3)]
    out = set()
    for _ in range(4):
        out.add("".join("".join(r) for r in g))
        g = [[g[2 - c][r] for c in range(3)] for r in range(3)]
    return out


def test_multiple_lighting_states(rig, cfg, tmp_path):
    robot, ch, cam = rig
    cfg2 = RobotConfig({**cfg.raw, "scan": {**cfg.raw["scan"], "lighting": ["white", "red", "blue"]}})
    manifest = Scanner(ch, cam, cfg2).scan(tmp_path / "scan")
    assert len(manifest["photos"]) == 18
    assert cam.captures == 18
    assert {p["lighting"] for p in manifest["photos"]} == {"white", "red", "blue"}


def test_bad_sequence_is_rejected(rig, cfg):
    _, ch, cam = rig
    cfg2 = RobotConfig({**cfg.raw, "scan": {"sequence": ["photo", "y", "photo"]}})
    with pytest.raises(ValueError):
        Scanner(ch, cam, cfg2)
