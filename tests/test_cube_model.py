import random

import pytest

from rcubed.cube_model import FACES, SOLVED, CubeModel, invert, rotations_to_home

# Kociemba's own example (README of the kociemba package).
KOCIEMBA_EXAMPLE = "DRLUUBFBRBLURRLRUBLRDDFDLFUFUFFDBRDUBRUFLLFDDBFLUBLRBD"
KOCIEMBA_EXAMPLE_SOLUTION = "D2 R' D' F2 B D R2 D2 R' F2 D' F2 U' B2 L2 U2 D R2 U"


@pytest.mark.parametrize("m", list("URFDLBxyz"))
def test_four_quarter_turns_are_identity(m):
    assert CubeModel().apply(" ".join([m] * 4)).state == SOLVED


@pytest.mark.parametrize("m", list("URFDLBxyz"))
def test_prime_and_double(m):
    assert CubeModel().apply(f"{m} {m}'").state == SOLVED
    assert CubeModel().apply(f"{m}2 {m}2").state == SOLVED
    assert CubeModel().apply(f"{m} {m}").state == CubeModel().apply(f"{m}2").state


def test_sexy_move_order_six():
    assert CubeModel().apply(" ".join(["R U R' U'"] * 6)).state == SOLVED


def test_kociemba_example_solution_solves_it():
    m = CubeModel(KOCIEMBA_EXAMPLE).apply(KOCIEMBA_EXAMPLE_SOLUTION)
    assert m.is_solved


def test_each_move_is_a_permutation_with_fixed_centres():
    for m in "URFDLB":
        c = CubeModel().apply(m)
        assert sorted(c.state) == sorted(SOLVED)
        assert all(c.center(f) == f for f in FACES)


@pytest.mark.parametrize(
    "conj, equiv",
    [
        ("y R y'", "B"),   # after y the old B face sits at R
        ("y' R y", "F"),   # after y' the old F face sits at R
        ("y L y'", "F"),
        ("x U x'", "F"),   # after x the old F face sits on top
        ("x' U x", "B"),
        ("x R x'", "R"),
        ("z U z'", "L"),
        ("y U y'", "U"),
    ],
)
def test_rotation_conjugation(conj, equiv):
    assert CubeModel().apply(conj).state == CubeModel().apply(equiv).state


def test_rotation_moves_centres():
    m = CubeModel().apply("y")
    assert m.center("F") == "R" and m.center("L") == "F" and m.center("B") == "L" and m.center("R") == "B"
    assert m.position_of("F") == "L"
    m = CubeModel().apply("x")
    assert m.center("U") == "F" and m.center("F") == "D" and m.center("D") == "B" and m.center("B") == "U"


def test_kociemba_string_relabels_by_centres():
    scr = "R U F' L2 D B"
    a = CubeModel().apply(scr)
    b = CubeModel().apply(scr + " y x")
    assert a.kociemba_string() == a.state
    assert b.kociemba_string() != b.state  # centres moved...
    assert CubeModel().apply("y x").kociemba_string() == SOLVED  # ...but relabelling fixes it
    centres = [b.kociemba_string()[i * 9 + 4] for i in range(6)]
    assert "".join(centres) == FACES


def test_invert():
    scr = "R U2 F' L D2 B'"
    assert CubeModel().apply(scr).apply(invert(scr)).state == SOLVED


def test_rotations_to_home_reaches_every_orientation():
    random.seed(1)
    for _ in range(50):
        seq = " ".join(random.choice(["x", "x'", "y", "y'", "z", "z'"]) for _ in range(random.randint(1, 6)))
        m = CubeModel().apply(seq)
        path = rotations_to_home(m)
        assert len(path) <= 3
        assert m.apply(" ".join(path)).is_home


def test_random_scramble_roundtrip_with_kociemba():
    kociemba = pytest.importorskip("kociemba")
    random.seed(7)
    moves = [f + s for f in "URFDLB" for s in ("", "'", "2")]
    for _ in range(5):
        scr = " ".join(random.choice(moves) for _ in range(20))
        m = CubeModel().apply(scr)
        sol = kociemba.solve(m.kociemba_string())
        assert m.apply(sol).is_solved
