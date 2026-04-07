from __future__ import annotations

from typing import Dict

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

    bw = parasites_lab > 0
    structure = np.ones((2 * merge_radius + 1, 2 * merge_radius + 1), dtype=bool)
    bw_dil = binary_dilation(bw, structure=structure)
    merged, _ = ndi_label(bw_dil)
    return merged.astype(np.uint16, copy=False)


def _nearest_cell_distance_and_id(cells_lab: np.ndarray, pmask: np.ndarray) -> tuple[int, float]:
    cell_bw = cells_lab > 0
    if not cell_bw.any():
        return 0, float("inf")

    ys, xs = np.where(pmask)
    if ys.size == 0:
        return 0, float("inf")

    dist_map, (iy, ix) = distance_transform_edt(~cell_bw, return_indices=True)
    y0 = int(np.round(float(ys.mean())))
    x0 = int(np.round(float(xs.mean())))
    ny, nx = int(iy[y0, x0]), int(ix[y0, x0])
    cid = int(cells_lab[ny, nx])
    distance = float(dist_map[y0, x0])
    return cid, distance


def assign_parasites_with_confidence(
    cells_lab: np.ndarray,
    parasites_lab: np.ndarray,
    sigma: float = 40.0,
    threshold: float = 0.5,
) -> Dict[str, object]:
    """
    Asigna parasitos a celulas con una confianza en [0, 1].

    - Si hay solape con una celula, la confianza es 1.0.
    - Si no hay solape, se usa la celula mas cercana y una decaida exponencial
      segun la distancia al borde celular.
    - Solo se cuentan como asignados los casos con confianza >= threshold.
    """
    c_total = int(cells_lab.max())
    p_total = int(parasites_lab.max())
    counts = np.zeros(c_total, dtype=int)
    confidences: list[float] = []
    # confident_confidences: list[float] = []
    assigned_parasites = 0
    unassigned_parasites = 0

    if c_total == 0 or p_total == 0:
        return {
            "infected_cells": 0,
            "parasites_per_cell": counts,
            "assigned_parasites": assigned_parasites,
            "unassigned_parasites": p_total,
            #"mean_assignment_confidence": 0.0,
            #"mean_confident_assignment_confidence": 0.0,
        }

    safe_sigma = max(float(sigma), 1e-6)

    for pid in range(1, p_total + 1):
        pmask = parasites_lab == pid
        if not pmask.any():
            continue

        overlap = np.bincount(cells_lab[pmask].ravel(), minlength=c_total + 1)
        overlap[0] = 0
        cid = int(overlap.argmax())

        if overlap[cid] > 0:
            confidence = 1.0
        else:
            cid, distance = _nearest_cell_distance_and_id(cells_lab, pmask)
            if cid <= 0:
                unassigned_parasites += 1
                confidences.append(0.0)
                continue
            confidence = float(np.exp(-distance / safe_sigma))

        confidences.append(confidence)

        if confidence >= threshold:
            counts[cid - 1] += 1
            assigned_parasites += 1
            #confident_confidences.append(confidence)
        else:
            unassigned_parasites += 1

    infected_cells = int((counts > 0).sum())
    mean_assignment_confidence = float(np.mean(confidences)) if confidences else 0.0
    #mean_confident_assignment_confidence = (
    #    float(np.mean(confident_confidences)) if confident_confidences else 0.0
    #)

    return {
        "infected_cells": infected_cells,
        "parasites_per_cell": counts,
        "assigned_parasites": assigned_parasites,
        "unassigned_parasites": unassigned_parasites,
        "mean_assignment_confidence": mean_assignment_confidence,
        #"mean_confident_assignment_confidence": mean_confident_assignment_confidence,
    }
