from __future__ import annotations
from typing import Tuple
import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt, label as ndi_label

def merge_parasites(parasites_lab: np.ndarray, merge_radius: int = 2) -> np.ndarray:
    """
    Une instancias de parasitos cercanas para reducir doble conteo.

    Requiere scipy; si no esta disponible, devuelve la mascara original.
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

    if distance_transform_edt is not None:
        _, (iy, ix) = distance_transform_edt(~cell_bw, return_indices=True)
        ys, xs = np.where(pmask)
        if ys.size == 0:
            return 0
        y0 = int(np.round(float(ys.mean())))
        x0 = int(np.round(float(xs.mean())))
        ny, nx = int(iy[y0, x0]), int(ix[y0, x0])
        return int(cells_lab[ny, nx])

    ys, xs = np.where(pmask)
    if ys.size == 0:
        return 0
    py, px = float(ys.mean()), float(xs.mean())

    best_cid = 0
    best_d2 = float("inf")
    for cid in range(1, int(cells_lab.max()) + 1):
        cyx = np.where(cells_lab == cid)
        if cyx[0].size == 0:
            continue
        cy, cx = float(cyx[0].mean()), float(cyx[1].mean())
        d2 = (cy - py) ** 2 + (cx - px) ** 2
        if d2 < best_d2:
            best_d2 = d2
            best_cid = cid
    return int(best_cid)


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
