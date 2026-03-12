from __future__ import annotations
import numpy as np
from csbdeep.data import PercentileNormalizer
from stardist.models import StarDist2D

_MODEL = None
_MODEL_NAME = "2D_versatile_fluo"

def _get_stardist_model(model_name: str = _MODEL_NAME):
    global _MODEL
    if _MODEL is None:
        _MODEL = StarDist2D.from_pretrained(model_name)
    return _MODEL

def segment_parasites(
    img2d: np.ndarray,
    prob_thresh: float = 0.5,
    nms_thresh: float = 0.3,
    model_name: str = _MODEL_NAME,
):

    model = _get_stardist_model(model_name=model_name)
    normalizer = PercentileNormalizer()
    labels, details = model.predict_instances(
        img2d,
        prob_thresh=prob_thresh,
        nms_thresh=nms_thresh,
        normalizer=normalizer,
    )
    return labels.astype(np.int32, copy=False), details
