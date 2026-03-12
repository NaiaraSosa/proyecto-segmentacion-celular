from __future__ import annotations

from typing import Tuple

import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt, label as ndi_label


def filter_cells_by_area(cells_lab: np.ndarray, min_area: int) -> np.ndarray:
    """
    Conserva solo celulas con area >= min_area y re-etiqueta desde 1..N.
    """
    if cells_lab.size == 0 or int(cells_lab.max()) == 0:
        return cells_lab.astype(np.uint16, copy=False)

    if min_area <= 0:
        return cells_lab.astype(np.uint16, copy=False)

    areas = np.bincount(cells_lab.ravel())
    keep_ids = np.where(areas >= int(min_area))[0]
    keep_ids = keep_ids[keep_ids != 0]

    out = np.zeros_like(cells_lab, dtype=np.uint16)
    for new_id, old_id in enumerate(keep_ids, start=1):
        out[cells_lab == old_id] = new_id
    return out


def filter_parasites_by_area(parasites_lab: np.ndarray, max_area: int) -> np.ndarray:
    """
    Conserva solo parasitos con area <= max_area y re-etiqueta desde 1..N.
    """
    if parasites_lab.size == 0 or int(parasites_lab.max()) == 0:
        return parasites_lab.astype(np.uint16, copy=False)

    if max_area <= 0:
        return parasites_lab.astype(np.uint16, copy=False)

    areas = np.bincount(parasites_lab.ravel())
    keep_ids = np.where(areas <= int(max_area))[0]
    keep_ids = keep_ids[keep_ids != 0]

    out = np.zeros_like(parasites_lab, dtype=np.uint16)
    for new_id, old_id in enumerate(keep_ids, start=1):
        out[parasites_lab == old_id] = new_id
    return out


def merge_parasites(parasites_lab: np.ndarray, merge_radius: int = 2) -> np.ndarray:
    """
    Une instancias de parasitos cercanas para reducir doble conteo.
    """
    if parasites_lab.size == 0 or int(parasites_lab.max()) == 0:
        return parasites_lab.astype(np.uint16, copy=False)

    if binary_dilation is None or ndi_label is None:
        return parasites_lab.astype(np.uint16, copy=False)

    bw = parasites_lab > 0
    structure = np.ones((2 * merge_radius + 1, 2 * merge_radius + 1), dtype=bool)
    bw_dil = binary_dilation(bw, structure=structure)
    merged, _ = ndi_label(bw_dil)
    return merged.astype(np.uint16, copy=False)


def assign_by_nearest_cell(cells_lab: np.ndarray, pmask: np.ndarray) -> int:
    """
    Asigna un parasito a la celula mas cercana cuando no hay solapamiento.
    """
    cell_bw = cells_lab > 0
    if not cell_bw.any():
        return 0

    ys, xs = np.where(pmask)
    if ys.size == 0:
        return 0
    _, (iy, ix) = distance_transform_edt(~cell_bw, return_indices=True)
    y0 = int(np.round(float(ys.mean())))
    x0 = int(np.round(float(xs.mean())))
    ny, nx = int(iy[y0, x0]), int(ix[y0, x0])
    return int(cells_lab[ny, nx])


def conteo_infeccion(cells_lab: np.ndarray, parasites_lab: np.ndarray) -> Tuple[int, np.ndarray, int]:
    """
    Cuenta celulas infectadas y parasitos por celula.
    """
    c_total = int(cells_lab.max())
    p_total = int(parasites_lab.max())
    counts = np.zeros(c_total, dtype=int)
    unassigned = 0

    if c_total == 0 or p_total == 0:
        return 0, counts, unassigned

    for pid in range(1, p_total + 1):
        pmask = parasites_lab == pid
        if not pmask.any():
            continue

        overlap = np.bincount(cells_lab[pmask].ravel(), minlength=c_total + 1)
        overlap[0] = 0
        cid = int(overlap.argmax())

        if overlap[cid] > 0:
            counts[cid - 1] += 1
            continue

        nearest_cid = assign_by_nearest_cell(cells_lab, pmask)
        if nearest_cid > 0:
            counts[nearest_cid - 1] += 1
        else:
            unassigned += 1

    infected = int((counts > 0).sum())
    return infected, counts, unassigned
