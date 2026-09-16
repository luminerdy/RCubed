"""54-facelet cube model in Kociemba facelet order, with whole-cube rotations.

Facelet numbering (Kociemba):

             U1 U2 U3
             U4 U5 U6
             U7 U8 U9
    L1 L2 L3 F1 F2 F3 R1 R2 R3 B1 B2 B3
    L4 L5 L6 F4 F5 F6 R4 R5 R6 B4 B5 B6
    L7 L8 L9 F7 F8 F9 R7 R8 R9 B7 B8 B9
             D1 D2 D3
             D4 D5 D6
             D7 D8 D9

String index = face offset (U0 R9 F18 D27 L36 B45) + facelet-1.
Each face is read top-left to bottom-right as seen from outside the cube with
the cube held in the standard orientation (U on top, F facing you).

The model is a *physical-frame* model: the six positions U R F D L B are the
robot's fixed positions, and the letters stored in the state are sticker
identities (which face they belong to on the solved cube, i.e. the colour).
Whole-cube rotations x y z move stickers between positions, so after a `y` the
letter at the F centre is 'R'. That is exactly what the camera sees.
"""
from __future__ import annotations

import re

FACES = "URFDLB"
OFFSET = {f: i * 9 for i, f in enumerate(FACES)}
SOLVED = "".join(f * 9 for f in FACES)
TOKEN_RE = re.compile(r"^([URFDLBxyz])(['2]?)$")


# ── permutation construction ──────────────────────────────────────────────
# A permutation `p` means: new_state[i] = old_state[p[i]].

def _cw_within(o: int) -> dict[int, int]:
    """Rotate a face's 9 stickers clockwise (as seen from outside)."""
    return {o + r * 3 + c: o + (2 - c) * 3 + r for r in range(3) for c in range(3)}


def _ccw_within(o: int) -> dict[int, int]:
    return {o + r * 3 + c: o + c * 3 + (2 - r) for r in range(3) for c in range(3)}


def _from_cycles(cycles: list[tuple[int, ...]]) -> list[int]:
    p = list(range(54))
    for cyc in cycles:  # sticker at cyc[i] moves to cyc[i+1]
        for i in range(len(cyc)):
            p[cyc[(i + 1) % len(cyc)]] = cyc[i]
    return p


def _face_cycles(f: str) -> list[tuple[int, ...]]:
    o = OFFSET[f]
    return [(o, o + 2, o + 8, o + 6), (o + 1, o + 5, o + 7, o + 3)]


U, R, F, D, L, B = (OFFSET[f] for f in FACES)

_MOVE_CYCLES = {
    "U": _face_cycles("U") + [(F + 0, L + 0, B + 0, R + 0), (F + 1, L + 1, B + 1, R + 1), (F + 2, L + 2, B + 2, R + 2)],
    "R": _face_cycles("R") + [(F + 2, U + 2, B + 6, D + 2), (F + 5, U + 5, B + 3, D + 5), (F + 8, U + 8, B + 0, D + 8)],
    "F": _face_cycles("F") + [(U + 6, R + 0, D + 2, L + 8), (U + 7, R + 3, D + 1, L + 5), (U + 8, R + 6, D + 0, L + 2)],
    "D": _face_cycles("D") + [(F + 6, R + 6, B + 6, L + 6), (F + 7, R + 7, B + 7, L + 7), (F + 8, R + 8, B + 8, L + 8)],
    "L": _face_cycles("L") + [(U + 0, F + 0, D + 0, B + 8), (U + 3, F + 3, D + 3, B + 5), (U + 6, F + 6, D + 6, B + 2)],
    "B": _face_cycles("B") + [(U + 2, L + 0, D + 6, R + 8), (U + 1, L + 3, D + 7, R + 5), (U + 0, L + 6, D + 8, R + 2)],
}


def _rotation_perm(axis: str) -> list[int]:
    p = list(range(54))
    if axis == "y":  # like U: R->F, F->L, L->B, B->R
        for i in range(9):
            p[F + i], p[L + i], p[B + i], p[R + i] = R + i, F + i, L + i, B + i
        p_extra = {**_cw_within(U), **_ccw_within(D)}
    elif axis == "x":  # like R: F->U, U->B, B->D, D->F
        for i in range(9):
            p[U + i], p[B + i], p[D + i], p[F + i] = F + i, U + (8 - i), B + (8 - i), D + i
        p_extra = {**_cw_within(R), **_ccw_within(L)}
    elif axis == "z":  # like F: U->R, R->D, D->L, L->U (each rotated cw as it moves)
        p_extra = {**_cw_within(F), **_ccw_within(B)}
        for src, dst in (("U", "R"), ("R", "D"), ("D", "L"), ("L", "U")):
            os_, od = OFFSET[src], OFFSET[dst]
            for r in range(3):
                for c in range(3):
                    p_extra[od + r * 3 + c] = os_ + (2 - c) * 3 + r
    else:
        raise ValueError(axis)
    for k, v in p_extra.items():
        p[k] = v
    return p


PERMS: dict[str, list[int]] = {m: _from_cycles(c) for m, c in _MOVE_CYCLES.items()}
PERMS.update({a: _rotation_perm(a) for a in "xyz"})


def _compose_pow(p: list[int], n: int) -> list[int]:
    out = list(range(54))
    for _ in range(n):
        out = [out[p[i]] for i in range(54)]
    return out


# Every token -> permutation, e.g. "R'", "U2", "y".
ALL_PERMS: dict[str, list[int]] = {}
for _m, _p in PERMS.items():
    ALL_PERMS[_m] = _p
    ALL_PERMS[_m + "2"] = _compose_pow(_p, 2)
    ALL_PERMS[_m + "'"] = _compose_pow(_p, 3)


def parse_moves(seq: str) -> list[str]:
    tokens = seq.replace(",", " ").split()
    for t in tokens:
        if not TOKEN_RE.match(t):
            raise ValueError(f"bad move token: {t!r}")
    return tokens


def invert(seq: str) -> str:
    out = []
    for t in reversed(parse_moves(seq)):
        if t.endswith("'"):
            out.append(t[0])
        elif t.endswith("2"):
            out.append(t)
        else:
            out.append(t + "'")
    return " ".join(out)


class CubeModel:
    __slots__ = ("state",)

    def __init__(self, state: str = SOLVED):
        if len(state) != 54:
            raise ValueError("state must be 54 characters")
        self.state = state

    def copy(self) -> "CubeModel":
        return CubeModel(self.state)

    def apply(self, seq: str) -> "CubeModel":
        for t in parse_moves(seq):
            p = ALL_PERMS[t]
            self.state = "".join(self.state[p[i]] for i in range(54))
        return self

    # ── queries ─────────────────────────────────────────────────────────
    def face(self, f: str) -> str:
        """9 stickers of the face at physical position f, reading order."""
        o = OFFSET[f]
        return self.state[o : o + 9]

    def center(self, f: str) -> str:
        """Sticker identity (colour) currently at the centre of position f."""
        return self.state[OFFSET[f] + 4]

    def position_of(self, sticker_face: str) -> str:
        """Physical position where the given face (by centre colour) currently sits."""
        for f in FACES:
            if self.center(f) == sticker_face:
                return f
        raise ValueError(sticker_face)

    @property
    def is_solved(self) -> bool:
        return all(len(set(self.face(f))) == 1 for f in FACES)

    @property
    def is_home(self) -> bool:
        """True when every face sits at its own position (no net rotation)."""
        return all(self.center(f) == f for f in FACES)

    def kociemba_string(self) -> str:
        """Relabel stickers by which centre they match. The result is a valid
        solver input in any orientation, and the solution it yields is written
        in the cube's *current* orientation (so execute it before rotating)."""
        by_center = {self.center(f): f for f in FACES}
        if len(by_center) != 6:
            raise ValueError("centres are not six distinct stickers")
        return "".join(by_center[s] for s in self.state)

    # ── dunder ──────────────────────────────────────────────────────────
    def __eq__(self, other: object) -> bool:
        return isinstance(other, CubeModel) and self.state == other.state

    def __hash__(self) -> int:
        return hash(self.state)

    def __repr__(self) -> str:
        return f"CubeModel({self.state!r})"

    def pretty(self) -> str:
        u, r, f, d, l, b = (self.face(x) for x in FACES)
        rows = []
        for i in range(3):
            rows.append("      " + " ".join(u[i * 3 : i * 3 + 3]))
        for i in range(3):
            rows.append(
                " ".join(l[i * 3 : i * 3 + 3]) + " " + " ".join(f[i * 3 : i * 3 + 3]) + " "
                + " ".join(r[i * 3 : i * 3 + 3]) + " " + " ".join(b[i * 3 : i * 3 + 3])
            )
        for i in range(3):
            rows.append("      " + " ".join(d[i * 3 : i * 3 + 3]))
        return "\n".join(rows)


ROTATION_TOKENS = ("y", "y'", "y2", "x", "x'", "x2")


def rotations_to_home(model: CubeModel, max_depth: int = 4) -> list[str]:
    """Shortest sequence of x/y rotations that brings the model's orientation
    home (breadth-first over the 24-element rotation group)."""
    if model.is_home:
        return []
    frontier = [(model.copy(), [])]
    seen = {tuple(model.center(f) for f in FACES)}
    for _ in range(max_depth):
        nxt = []
        for m, path in frontier:
            for tok in ROTATION_TOKENS:
                m2 = m.copy().apply(tok)
                key = tuple(m2.center(f) for f in FACES)
                if key in seen:
                    continue
                if m2.is_home:
                    return path + [tok]
                seen.add(key)
                nxt.append((m2, path + [tok]))
        frontier = nxt
    raise RuntimeError("orientation not reachable with x/y rotations")
