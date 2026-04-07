from __future__ import annotations

from typing import Dict

import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt, label as ndi_label


def filter_cells_by_area(cells_lab: np.ndarray, min_area: int) -> np.ndarray:
    """
    Filtra células por área mínima y re-etiqueta las válidas.

    Elimina detecciones de células que son demasiado pequeñas (probablemente
    ruido o fragmentos) y reasigna IDs consecutivos desde 1 a las células
    que pasan el filtro.

    Args:
        cells_lab: Array 2D con máscaras de células (IDs únicos por célula).
        min_area: Área mínima en píxeles. Células más pequeñas se eliminan.

    Returns:
        Array 2D uint16 con células filtradas. IDs re-etiquetados desde 1..N.
        Células eliminadas se convierten en fondo (0).
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
    Filtra parásitos por área máxima y re-etiqueta los válidos.

    Elimina detecciones de parásitos que son demasiado grandes (probablemente
    ruido, agregados o células mal segmentadas) y reasigna IDs consecutivos
    desde 1 a los parásitos que pasan el filtro.

    Args:
        parasites_lab: Array 2D con máscaras de parásitos (IDs únicos por parásito).
        max_area: Área máxima en píxeles. Parásitos más grandes se eliminan.

    Returns:
        Array 2D uint16 con parásitos filtrados. IDs re-etiquetados desde 1..N.
        Parásitos eliminados se convierten en fondo (0).
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
    Une parásitos cercanos para reducir doble conteo.

    Cuando StarDist detecta parásitos muy juntos, puede segmentarlos como
    objetos separados aunque sean el mismo parásito. Esta función los
    agrupa usando dilatación morfológica.

    Args:
        parasites_lab: Array 2D con máscaras de parásitos (IDs únicos).
        merge_radius: Radio de dilatación en píxeles (default: 2).
            Parásitos separados por ≤ 2*radius se unen.

    Returns:
        Array 2D uint16 con parásitos fusionados. IDs re-etiquetados desde 1..N.

    Notes:
        - Usa binary_dilation para "inflar" las máscaras
        - Luego ndi_label para identificar componentes conectados
        - Reduce falsos positivos de segmentación por proximidad
        - merge_radius=2 significa que parásitos separados por ≤4px se unen
    """
    if parasites_lab.size == 0 or int(parasites_lab.max()) == 0:
        return parasites_lab.astype(np.uint16, copy=False)

    bw = parasites_lab > 0
    structure = np.ones((2 * merge_radius + 1, 2 * merge_radius + 1), dtype=bool)
    bw_dil = binary_dilation(bw, structure=structure)
    merged, _ = ndi_label(bw_dil)
    return merged.astype(np.uint16, copy=False)


def nearest_cell_distance(cells_lab: np.ndarray, pmask: np.ndarray) -> tuple[int, float]:
    """
    Encuentra la célula más cercana a un parásito y calcula distancia.

    Cuando un parásito no solapa directamente con una célula, esta función
    busca la célula más cercana al parásito y calcula la distancia euclidiana
    desde el centro del parásito hasta el borde de la célula más cercana.

    Args:
        cells_lab: Array 2D con máscaras de células (IDs únicos).
        pmask: Array 2D booleano, máscara del parásito (True = píxeles del parásito).

    Returns:
        Tuple (cell_id, distance):
        - cell_id: ID de la célula más cercana (0 si no hay células)
        - distance: Distancia euclidiana desde centro parásito a borde célula
    """
    cell_bw = cells_lab > 0
    if not cell_bw.any():
        return 0, float("inf")

    ys, xs = np.where(pmask)
    if ys.size == 0:
        return 0, float("inf")

    # Distance Transform: calcula distancia a borde de célula más cercano
    dist_map, (iy, ix) = distance_transform_edt(~cell_bw, return_indices=True)
    # Centro del parásito (promedio de sus píxeles)
    y0 = int(np.round(float(ys.mean())))
    x0 = int(np.round(float(xs.mean())))
    # Encontrar pixel más cercano en la célula
    ny, nx = int(iy[y0, x0]), int(ix[y0, x0])
    cid = int(cells_lab[ny, nx])
    distance = float(dist_map[y0, x0])
    return cid, distance


def assign_parasites(
    cells_lab: np.ndarray,
    parasites_lab: np.ndarray,
    sigma: float = 40.0,
    threshold: float = 0.3,
) -> Dict[str, object]:
    """
    Asigna parásitos a células usando lógica de solapamiento y proximidad.

    Usa dos estrategias:
    1. SOLAPAMIENTO DIRECTO: Si un parásito está dentro de una célula → confianza=1.0
    2. PROXIMIDAD: Si no solapa, busca célula más cercana → confianza=exp(-distancia/sigma)

    Args:
        cells_lab: Array 2D con máscaras de células (IDs únicos, 0=fondo).
        parasites_lab: Array 2D con máscaras de parásitos (IDs únicos, 0=fondo).
        sigma: Parámetro de escala para decaimiento exponencial (default: 40.0 píxeles).
            Controla qué tan rápido cae la confianza con la distancia.
            sigma=40: A 40px de distancia, confianza ≈ 0.37
        threshold: Confianza mínima para considerar asignación válida (default: 0.3).
            Asignaciones con confianza < threshold se marcan como "no asignadas".

    Returns:
        Dict con resultados de asignación:
        - infected_cells: Número de células con al menos 1 parásito asignado
        - parasites_per_cell: Array con conteo de parásitos por célula (índice = ID-1)
        - assigned_parasites: Parásitos asignados con confianza ≥ threshold
        - unassigned_parasites: Parásitos con confianza < threshold
        - mean_assignment_confidence: Confianza promedio de TODAS las asignaciones
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
            "mean_assignment_confidence": 0.0,
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

        # caso 1: solapamiento directo → confianza máxima
        if overlap[cid] > 0:
            confidence = 1.0
        # caso 2: no solapa → buscar célula más cercana y calcular confianza por distancia
        else:
            cid, distance = nearest_cell_distance(cells_lab, pmask)
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
