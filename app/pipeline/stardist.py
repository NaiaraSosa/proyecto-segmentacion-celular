from __future__ import annotations
import numpy as np
from csbdeep.utils import normalize
from stardist.models import StarDist2D

_MODEL = None
_MODEL_NAME = "2D_versatile_fluo"

def _get_stardist_model(model_name: str = _MODEL_NAME):
    global _MODEL
    if _MODEL is None:
        _MODEL = StarDist2D.from_pretrained(model_name)
    return _MODEL

def _to_2d(img: np.ndarray) -> np.ndarray:
    x = np.asarray(img)
    x = np.squeeze(x)

    if x.ndim == 2:
        return x
    if x.ndim == 3 and x.shape[-1] <= 4:   # (Y, X, C)
        return x[..., 0]
    if x.ndim == 3 and x.shape[0] <= 4:    # (C, Y, X)
        return x[0, ...]
    if x.ndim == 3:                        # (Z, Y, X) u otro
        return x[0, ...]
    raise ValueError(f"No se pudo convertir a 2D. shape={x.shape}")

def segment_parasites(
    img2d: np.ndarray,
    prob_thresh: float = 0.5,
    nms_thresh: float = 0.3,
    model_name: str = _MODEL_NAME,
):
    x = _to_2d(img2d).astype(np.float32, copy=False)
    x_n = normalize(x)

    model = _get_stardist_model(model_name=model_name)
    labels, details = model.predict_instances(
        x_n,
        prob_thresh=prob_thresh,
        nms_thresh=nms_thresh,
    )
    return labels.astype(np.int32, copy=False), details