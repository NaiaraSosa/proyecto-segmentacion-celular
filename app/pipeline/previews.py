from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


_PALETTE = np.array(
    [
        [230, 57, 70],
        [29, 161, 242],
        [67, 170, 139],
        [244, 162, 97],
        [131, 56, 236],
        [255, 190, 11],
        [42, 157, 143],
        [239, 71, 111],
        [6, 214, 160],
        [17, 138, 178],
        [255, 127, 80],
        [144, 190, 109],
    ],
    dtype=np.uint8,
)


def build_input_preview(img2d: np.ndarray) -> np.ndarray:
    x = img2d.astype(np.float32, copy=False)
    p1, p99 = np.percentile(x, [1, 99])
    if p99 > p1:
        x = np.clip((x - p1) / (p99 - p1), 0.0, 1.0)
    else:
        x = np.zeros_like(x, dtype=np.float32)
    gray = (x * 255).astype(np.uint8)
    return np.stack([gray, gray, gray], axis=-1)


def build_instance_preview(labels: np.ndarray) -> np.ndarray:
    if labels.size == 0:
        return np.zeros((1, 1, 3), dtype=np.uint8)

    h, w = labels.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)

    positive = labels > 0
    if not positive.any():
        return rgb

    color_idx = labels[positive] % len(_PALETTE)
    rgb[positive] = _PALETTE[color_idx]
    return rgb


def save_preview(path: Path, rgb: np.ndarray) -> None:
    Image.fromarray(rgb, mode="RGB").save(path)
