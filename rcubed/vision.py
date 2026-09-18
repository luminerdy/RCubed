"""Sticker colour classification.

The rig fixes where the nine stickers are in every photo, so vision reduces to
classifying nine small patches per face into six colours. Steps:

1. features: median L*a*b* over the central 40 % of each cell (median ignores the
   specular streaks a light leaves on glossy stickers);
2. a Gaussian classifier fitted on labelled scans (class means + pooled covariance,
   i.e. Mahalanobis distance to each colour);
3. constrained assignment over the whole cube: the six centres are known from the
   scan choreography, and each colour has exactly eight other stickers. Ambiguous
   orange/red or white/yellow patches get resolved by the counts.

Labelled scans come for free from `rcubed collect`: the robot scrambles a cube
with moves it tracks in the model, so every image carries its own ground truth.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .camera import cell_boxes
from .config import REPO_ROOT
from .cube_model import FACES

MODELS_DIR = REPO_ROOT / "models"
DEFAULT_MODEL = MODELS_DIR / "colors.json"
CENTRAL_FRACTION = 0.4


# ── features ──────────────────────────────────────────────────────────────

def cell_features(frame_bgr: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    """(9, 3) median L*a*b* of the central patch of each cell, reading order."""
    import cv2

    lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    out = []
    for x1, y1, x2, y2 in cell_boxes(box):
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        hw, hh = (x2 - x1) * CENTRAL_FRACTION / 2, (y2 - y1) * CENTRAL_FRACTION / 2
        patch = lab[int(cy - hh) : int(cy + hh), int(cx - hw) : int(cx + hw)].reshape(-1, 3)
        out.append(np.median(patch, axis=0))
    return np.array(out, dtype=np.float32)


def load_scan(scan_dir: Path) -> tuple[dict, list[np.ndarray]]:
    """Manifest plus one (9, 3) feature array per photo, in manifest order."""
    import cv2

    scan_dir = Path(scan_dir)
    manifest = json.loads((scan_dir / "manifest.json").read_text())
    box = tuple(manifest["camera"]["crop"])
    feats = []
    for p in manifest["photos"]:
        img = cv2.imread(str(scan_dir / p["file"]))
        if img is None:
            raise FileNotFoundError(scan_dir / p["file"])
        feats.append(cell_features(img, box))
    return manifest, feats


# ── classifier ────────────────────────────────────────────────────────────

@dataclass
class ColorModel:
    classes: list[str]
    means: np.ndarray        # (6, 3)
    inv_cov: np.ndarray      # (3, 3) pooled inverse covariance
    n_samples: int = 0
    lighting: str = "default"

    @classmethod
    def fit(cls, feats: np.ndarray, labels: list[str], lighting: str = "default") -> "ColorModel":
        feats = np.asarray(feats, dtype=np.float64)
        labels = np.asarray(labels)
        classes = [c for c in FACES if c in set(labels)]
        if len(classes) != 6:
            raise ValueError(f"need samples of all six colours, got {classes}")
        means = np.stack([feats[labels == c].mean(axis=0) for c in classes])
        resid = np.concatenate([feats[labels == c] - means[i] for i, c in enumerate(classes)])
        cov = np.cov(resid.T) if len(resid) > 3 else np.eye(3)
        cov = cov + np.eye(3) * 4.0  # regularise: a few units of L*a*b* noise
        return cls(classes, means, np.linalg.inv(cov), int(len(feats)), lighting)

    def distances(self, feats: np.ndarray) -> np.ndarray:
        """(n, 6) Mahalanobis distances to each class."""
        d = np.asarray(feats, dtype=np.float64)[:, None, :] - self.means[None, :, :]
        return np.sqrt(np.einsum("nci,ij,ncj->nc", d, self.inv_cov, d))

    def predict(self, feats: np.ndarray) -> list[str]:
        return [self.classes[i] for i in self.distances(feats).argmin(axis=1)]

    def save(self, path: Path = DEFAULT_MODEL) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "classes": self.classes,
                    "means": self.means.tolist(),
                    "inv_cov": self.inv_cov.tolist(),
                    "n_samples": self.n_samples,
                    "lighting": self.lighting,
                },
                indent=2,
            )
        )

    @classmethod
    def load(cls, path: Path = DEFAULT_MODEL) -> "ColorModel":
        d = json.loads(Path(path).read_text())
        return cls(d["classes"], np.array(d["means"]), np.array(d["inv_cov"]), d.get("n_samples", 0), d.get("lighting", "default"))


def train(scan_dirs: list[Path], lighting: str = "default") -> tuple[ColorModel, dict]:
    """Fit on every scan whose manifest says the cube state was known."""
    feats, labels, used = [], [], 0
    for d in scan_dirs:
        manifest, f = load_scan(d)
        if not manifest.get("known_state"):
            continue
        used += 1
        for p, cells in zip(manifest["photos"], f):
            if p["lighting"] != lighting:
                continue
            feats.extend(cells)
            labels.extend(p["stickers"])
    if not feats:
        raise ValueError("no labelled scans found")
    model = ColorModel.fit(np.array(feats), labels, lighting)
    pred = model.predict(np.array(feats))
    errors = sum(a != b for a, b in zip(pred, labels))
    return model, {"scans": used, "samples": len(labels), "training_errors": errors}


# ── whole-cube assignment ─────────────────────────────────────────────────

def _assign(cost: np.ndarray, capacity: int) -> list[int]:
    """Assign each row to a column, each column used at most `capacity` times,
    minimising total cost. Exact (Hungarian) when SciPy is present, else greedy."""
    n, k = cost.shape
    try:
        from scipy.optimize import linear_sum_assignment

        wide = np.repeat(cost, capacity, axis=1)  # n x (k*capacity)
        rows, cols = linear_sum_assignment(wide)
        out = [0] * n
        for r, c in zip(rows, cols):
            out[r] = c // capacity
        return out
    except ImportError:
        left = [capacity] * k
        out = [-1] * n
        order = sorted(range(n), key=lambda i: np.sort(cost[i])[1] - np.sort(cost[i])[0], reverse=True)
        for i in order:  # most confident first
            for c in np.argsort(cost[i]):
                if left[c] > 0:
                    out[i] = int(c)
                    left[c] -= 1
                    break
        return out


def classify_scan(scan_dir: Path, model: ColorModel, lighting: str | None = None) -> dict:
    """Read one scan into a 54-facelet string (home frame, letters by centre)."""
    manifest, feats = load_scan(scan_dir)
    lighting = lighting or model.lighting
    photos = [(p, f) for p, f in zip(manifest["photos"], feats) if p["lighting"] == lighting]
    if len(photos) != 6:
        raise ValueError(f"expected 6 photos for lighting {lighting!r}, got {len(photos)}")

    facelets = ["?"] * 54
    free_idx, free_cost, per_photo = [], [], []
    for p, f in photos:
        dist = model.distances(f)
        unconstrained = [model.classes[i] for i in dist.argmin(axis=1)]
        per_photo.append({"file": p["file"], "face": p["face"], "unconstrained": "".join(unconstrained)})
        for cell, (idx, d) in enumerate(zip(p["facelets"], dist)):
            if cell == 4:
                facelets[idx] = p["face"]  # centres are known from the choreography
            else:
                free_idx.append(idx)
                free_cost.append(d)

    cost = np.array(free_cost)
    choice = _assign(cost, capacity=8)
    margins = []
    for idx, c, d in zip(free_idx, choice, cost):
        facelets[idx] = model.classes[c]
        srt = np.sort(d)
        margins.append(float(srt[1] - srt[0]))
    return {
        "facelets": "".join(facelets),
        "photos": per_photo,
        "min_margin": float(min(margins)) if margins else 0.0,
        "changed_by_constraint": sum(
            1 for p, (pp, f) in zip(per_photo, photos)
            for cell, idx in enumerate(pp["facelets"])
            if cell != 4 and p["unconstrained"][cell] != facelets[idx]
        ),
    }
