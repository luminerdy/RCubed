"""Kociemba two-phase solver wrapper with validation."""
from __future__ import annotations

from collections import Counter

from .cube_model import FACES, CubeModel


class InvalidCubeError(ValueError):
    pass


def validate_facelets(s: str) -> None:
    if len(s) != 54:
        raise InvalidCubeError(f"expected 54 facelets, got {len(s)}")
    counts = Counter(s)
    bad = {k: v for k, v in counts.items() if k not in FACES or v != 9}
    if bad or len(counts) != 6:
        raise InvalidCubeError(f"need exactly 9 of each of {FACES}; got {dict(counts)}")
    centers = [s[i * 9 + 4] for i in range(6)]
    if centers != list(FACES):
        raise InvalidCubeError(f"centres must read URFDLB, got {''.join(centers)}")


def solve(cube: CubeModel | str) -> str:
    """Return a solution in standard notation ('' if already solved)."""
    s = cube.kociemba_string() if isinstance(cube, CubeModel) else cube
    validate_facelets(s)
    import kociemba  # lazy: not needed for simulation-only work

    try:
        sol = kociemba.solve(s)
    except Exception as e:  # kociemba raises bare ValueError with terse text
        raise InvalidCubeError(f"unsolvable cube state: {e}") from e
    return sol.strip()
