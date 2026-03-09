from __future__ import annotations
import numpy as np
from cellpose import models, io as cellpose_io

cellpose_io.logger_setup()  # Configura logging para Cellpose

_MODEL = None

def _get_cellpose_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = models.CellposeModel(gpu=True)
    return _MODEL

def segment_cells(
    img2d: np.ndarray,
    flow_threshold: float = 0.0,
    cellprob_threshold: float = 0.0,
    tile_norm_blocksize: int = 0,
    gpu: bool = True,
) -> np.ndarray:
    model = _get_cellpose_model()

    masks, flows, styles = model.eval(
        img2d,
        flow_threshold=flow_threshold,
        cellprob_threshold=cellprob_threshold,
        normalize={"tile_norm_blocksize": tile_norm_blocksize},
    )
    return masks.astype(np.int32, copy=False)