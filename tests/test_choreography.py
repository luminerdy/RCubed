import random

import pytest

from rcubed.backends import SimBackend
from rcubed.choreography import Choreographer
from rcubed.config import GRIPPERS, RobotConfig
from rcubed.cube_model import SOLVED, CubeModel, invert, rotations_to_home
from rcubed.robot import CollisionError, Robot, UnknownStateError, positions_swept


def homed(m: CubeModel) -> CubeModel:
    """The same cube configuration, rotated to the home orientation."""
    m = m.copy()
    return m.apply(" ".join(rotations_to_home(m)))


@pytest.fixture
def cfg():
    return RobotConfig.load()


@pytest.fixture
def rig(cfg, tmp_path):
    backend = SimBackend()
    robot = Robot(backend, cfg, state_file=tmp_path / "state.json")
    return backend, robot, Choreographer(robot, cfg)


# ── robot safety ─────────────────────────────────────────────────────────

def test_positions_swept():
    assert positions_swept("B", "C") == {"C"}
    assert positions_swept("D", "B") == {"C", "B"}
    assert positions_swept("A", "D") == {"B", "C", "D"}
    assert positions_swept("B", "B") == set()


def test_unknown_state_refuses_moves(rig):
    _, robot, _ = rig
    with pytest.raises(UnknownStateError):
        robot.set_gripper(0, "C")


def test_adjacent_collision_is_refused(rig):
    _, robot, ch = rig
    ch.safe_startup()
    robot.set_gripper(2, "C")
    with pytest.raises(CollisionError):
        robot.set_gripper(0, "C")
    with pytest.raises(CollisionError):
        robot.set_gripper(6, "A")
    robot.set_gripper(8, "A")  # opposite pair is fine
    robot.set_gripper(2, "B")
    robot.set_gripper(8, "B")
    robot.set_gripper(0, "C")  # now allowed


def test_sweep_through_c_is_checked(rig):
    _, robot, ch = rig
    ch.safe_startup()
    robot.set_gripper(6, "D")
    robot.set_gripper(2, "C")
    with pytest.raises(CollisionError):  # D->B passes through C while 2 sits at C
        robot.set_gripper(6, "B")


def test_state_roundtrip(rig, cfg, tmp_path):
    backend, robot, ch = rig
    ch.safe_startup()
    robot.set_gripper(2, "C")
    robot.save_state()
    r2 = Robot(SimBackend(), cfg, state_file=tmp_path / "state.json")
    assert r2.load_state()
    assert r2.gripper[2] == "C" and r2.rp[3] == "retracted"
    r2.invalidate_state()
    r3 = Robot(SimBackend(), cfg, state_file=tmp_path / "state.json")
    assert not r3.load_state()


def test_cube_orientation_survives_between_runs(cfg, tmp_path):
    state = tmp_path / "state.json"
    r1 = Robot(SimBackend(), cfg, state_file=state)
    c1 = Choreographer(r1, cfg)
    c1.safe_startup()
    c1.execute("R y", home=False)
    r1.close()
    r2 = Robot(SimBackend(), cfg, state_file=state)
    assert r2.load_state()
    c2 = Choreographer(r2, cfg)
    assert c2.model == c1.model
    assert c2.model.center("F") == "R"
    c2.execute("U", home=True)  # U means the face on top in the *current* frame
    assert c2.model == homed(CubeModel().apply("R y U"))


def test_no_state_file_means_no_persistence(cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    robot = Robot(SimBackend(), cfg, state_file=None)
    Choreographer(robot, cfg).safe_startup()
    robot.save_state()
    robot.invalidate_state()
    assert not list(tmp_path.iterdir())
    assert not robot.load_state()


# ── choreography ─────────────────────────────────────────────────────────

def test_safe_startup_ends_all_b_released(rig):
    _, robot, ch = rig
    ch.safe_startup()
    assert all(robot.gripper[g] == "B" for g in GRIPPERS)
    assert robot.holding() == ()


def test_load_position(rig, cfg):
    _, robot, ch = rig
    ch.load_position()
    assert {g: robot.gripper[g] for g in GRIPPERS} == cfg.load_position()
    assert robot.holding() == ()


def test_single_turn_sequence(rig, cfg):
    backend, robot, ch = rig
    ch.safe_startup()
    ch.engage_all()
    ch.move("R")
    assert ch.model == CubeModel().apply("R")
    assert all(robot.gripper[g] == "B" for g in GRIPPERS)
    assert len(robot.holding()) == 4
    # gripper 6 went to C then back to B
    targets = [(c, us) for kind, c, us in [e for e in backend.log if e[0] == "target"] if c == 6]
    assert cfg.gripper_us(6, "C") in [us for _, us in targets]


def test_front_move_rotates_then_turns_r_gripper(rig):
    _, robot, ch = rig
    ch.safe_startup()
    ch.execute("F", home=False)
    assert ch.rotations == 1
    assert ch.turns == 1
    assert ch.model.center("R") == "F"  # the F face now sits at the R gripper
    home = " ".join(rotations_to_home(ch.model))
    assert ch.model.copy().apply(home) == CubeModel().apply("F")


def test_consecutive_f_and_b_moves_share_one_rotation(rig):
    _, _, ch = rig
    ch.safe_startup()
    ch.execute("F F' F2 B", home=False)  # after y', F is at R and B is at L
    assert ch.rotations == 1
    assert ch.turns == 4
    assert homed(ch.model) == CubeModel().apply("F F' F2 B")


def test_execute_returns_home_and_matches_model(rig):
    _, robot, ch = rig
    ch.safe_startup()
    random.seed(3)
    moves = [f + s for f in "URFDLB" for s in ("", "'", "2")]
    scr = " ".join(random.choice(moves) for _ in range(25))
    ch.execute(scr)
    assert ch.model.is_home
    assert ch.model == CubeModel().apply(scr)
    assert all(robot.gripper[g] == "B" for g in GRIPPERS)
    assert len(robot.holding()) == 4


def test_execute_then_inverse_solves(rig):
    _, _, ch = rig
    ch.safe_startup()
    scr = "R U F' L2 D B' U2"
    ch.execute(scr + " " + invert(scr))
    assert ch.model.state == SOLVED


def test_x_rotations_and_mixed_sequence(rig):
    """Explicit rotations follow standard notation: after `y'`, `L` means the
    face now on the left. Helper rotations must not change that meaning."""
    _, robot, ch = rig
    ch.safe_startup()
    seq = "x R x' y' L y2 x2 U F B'"
    ch.execute(seq, home=True)
    assert ch.model.is_home
    assert ch.model == homed(CubeModel().apply(seq))


def test_z_rotation_is_rejected(rig):
    _, _, ch = rig
    ch.safe_startup()
    with pytest.raises(ValueError):
        ch.move("z")


def test_never_more_than_one_collision_free_rotation_pair_off_b(rig):
    """Invariant check over a long random run: at no point may two adjacent
    grippers both be off B/D (the guard would raise, but make sure the
    choreography never even tries)."""
    backend, robot, ch = rig
    ch.safe_startup()
    random.seed(11)
    moves = [f + s for f in "URFDLB" for s in ("", "'", "2")] + ["x", "x'", "y", "y'", "y2", "x2"]
    scr = " ".join(random.choice(moves) for _ in range(60))
    ch.execute(scr)
    assert ch.model.is_home
    assert ch.model == homed(CubeModel().apply(scr))


def test_simulated_solve_time_is_reported(rig):
    backend, _, ch = rig
    ch.safe_startup()
    ch.execute("R U R' U'")
    assert backend.clock > 0
