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


def test_pre_turn_reset_moves_opposite_pair_together(rig, cfg):
    """From the load pose (2 at C, 8 at A) a turn must reset 2 and 8 as a pair:
    arms 3 and 9 retract back-to-back, then both fingers move, then both engage."""
    backend, robot, ch = rig
    ch.load_position()
    ch.engage_all()
    start = len(backend.log)
    ch.move("R")
    log = [e for e in backend.log[start:] if e[0] == "target"]
    rp3_off = cfg.rp_us(3, "retracted")
    rp9_off = cfg.rp_us(9, "retracted")
    i3 = next(i for i, e in enumerate(log) if e[1] == 3 and e[2] == rp3_off)
    i9 = next(i for i, e in enumerate(log) if e[1] == 9 and e[2] == rp9_off)
    assert abs(i3 - i9) == 1  # released together, no move in between
    b2 = next(i for i, e in enumerate(log) if e[1] == 2 and e[2] == cfg.gripper_us(2, "B"))
    b8 = next(i for i, e in enumerate(log) if e[1] == 8 and e[2] == cfg.gripper_us(8, "B"))
    assert abs(b2 - b8) == 1  # swung to B together
    assert ch.model == CubeModel().apply("R")
    assert all(robot.gripper[g] == "B" for g in GRIPPERS)
    assert len(robot.holding()) == 4


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


def test_undo_rotation_sweeps_straight_back(rig, cfg):
    """After x the pair grips at A/C. x' just steps them back to B -- that sweep is
    the rotation, so no RP should move at all (no handover to the other pair)."""
    backend, robot, ch = rig
    ch.safe_startup()
    ch.engage_all()
    ch.rotate("x")
    assert (robot.gripper[0], robot.gripper[6]) == ("A", "C")
    start = len(backend.log)
    ch.rotate("x'")
    assert (robot.gripper[0], robot.gripper[6]) == ("B", "B")
    rp_moves = [e for e in backend.log[start:] if e[0] == "target" and e[1] in (1, 3, 7, 9)]
    assert rp_moves == []          # nothing was released or re-engaged
    assert set(robot.holding()) == {0, 6}
    assert ch.model.is_home
    assert ch.model == CubeModel()


@pytest.mark.parametrize("first,undo", [("x", "x'"), ("x'", "x"), ("y", "y'"), ("y'", "y")])
def test_undo_is_direct_on_both_axes(rig, cfg, first, undo):
    backend, robot, ch = rig
    ch.safe_startup()
    ch.engage_all()
    ch.rotate(first)
    start = len(backend.log)
    ch.rotate(undo)
    assert not [e for e in backend.log[start:] if e[0] == "target" and e[1] in (1, 3, 7, 9)]
    assert ch.model == CubeModel()


def test_repeating_a_rotation_still_resets_through_b(rig, cfg):
    """Two x moves in a row can't step directly -- gripper 0 would run off past A --
    so the second one goes back through B with a handover, as before."""
    backend, robot, ch = rig
    ch.safe_startup()
    ch.engage_all()
    ch.rotate("x")
    start = len(backend.log)
    ch.rotate("x")
    assert [e for e in backend.log[start:] if e[0] == "target" and e[1] in (1, 3, 7, 9)]
    assert (robot.gripper[0], robot.gripper[6]) == ("A", "C")
    assert ch.model == CubeModel().apply("x x")


def test_x2_toggles_directly_when_already_parked(rig, cfg):
    """After x', grippers 0/6 sit at C/A -- a following x2 should flip them straight
    to A/C (the x target) without a detour back through B."""
    backend, robot, ch = rig
    ch.safe_startup()
    ch.engage_all()
    ch.rotate("x'")
    assert robot.gripper[0] == "C" and robot.gripper[6] == "A"
    start = len(backend.log)
    ch.rotate("x2")
    targets = [e for e in backend.log[start:] if e[0] == "target" and e[1] in (0, 6)]
    assert not any(e[2] == cfg.gripper_us(e[1], "B") for e in targets)  # never routed through B
    assert robot.gripper[0] == "A" and robot.gripper[6] == "C"
    assert ch.model == CubeModel().apply("x' x2")


def test_x2_falls_back_to_two_quarter_turns_from_b(rig, cfg):
    """A bare x2 from the neutral pose (grippers at B) can't toggle -- it does two x's."""
    backend, robot, ch = rig
    ch.safe_startup()
    ch.engage_all()
    assert robot.gripper[0] == "B" and robot.gripper[6] == "B"
    start = len(backend.log)
    ch.rotate("x2")
    targets = [e for e in backend.log[start:] if e[0] == "target" and e[1] in (0, 6)]
    assert any(e[2] == cfg.gripper_us(e[1], "B") for e in targets)  # passes back through B
    assert ch.model == CubeModel().apply("x2")


def test_rotation_pair_speeds_are_synchronised(rig, cfg):
    """Both grippers of a tumble get speeds proportional to their travel, set before
    either target is sent, and cleared afterwards."""
    backend, robot, ch = rig
    ch.safe_startup()
    ch.engage_all()
    start = len(backend.log)
    ch.rotate("x")
    log = backend.log[start:]
    targets = cfg.rotation_targets("x")
    dist = {g: abs(cfg.gripper_us(g, p) - cfg.gripper_us(g, "B")) for g, p in targets.items()}
    longest = max(dist, key=dist.get)
    speeds = {}
    for i, e in enumerate(log):
        if e[0] == "speed" and e[1] in targets and e[1] not in speeds:
            speeds[e[1]] = (e[2], i)
    first_target = next(i for i, e in enumerate(log) if e[0] == "target" and e[1] in targets)
    assert speeds[longest][0] == cfg.rotation_speed("x")
    other = next(g for g in targets if g != longest)
    assert speeds[other][0] == round(cfg.rotation_speed("x") * dist[other] / dist[longest])
    assert all(i < first_target for _, i in speeds.values())
    # cleared afterwards
    last = {e[1]: e[2] for e in log if e[0] == "speed" and e[1] in targets}
    assert all(v == 0 for v in last.values())


def test_simulated_solve_time_is_reported(rig):
    backend, _, ch = rig
    ch.safe_startup()
    ch.execute("R U R' U'")
    assert backend.clock > 0
