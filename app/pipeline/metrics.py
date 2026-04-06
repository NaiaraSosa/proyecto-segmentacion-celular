from __future__ import annotations

from typing import Dict

import numpy as np

from app.pipeline.postprocess import assign_parasites_with_confidence


def compute_metrics(
    cells_lab: np.ndarray,
    parasites_lab: np.ndarray,
    assign_sigma: float = 40.0,
    assign_threshold: float = 0.5,
) -> Dict[str, object]:
    """
    Calcula metricas principales por imagen a partir de mascaras de instancias.
    """
    total_cells = int(cells_lab.max()) if cells_lab.size else 0
    total_parasites = int(parasites_lab.max()) if parasites_lab.size else 0

    assignment = assign_parasites_with_confidence(
        cells_lab,
        parasites_lab,
        sigma=assign_sigma,
        threshold=assign_threshold,
    )

    infected_cells = int(assignment["infected_cells"])
    parasites_per_cell = np.asarray(assignment["parasites_per_cell"], dtype=int)
    assigned_parasites = int(assignment["assigned_parasites"])
    unassigned_parasites = int(assignment["unassigned_parasites"])

    avg_parasites_per_infected_cell = (
        float(assigned_parasites / infected_cells) if infected_cells > 0 else 0.0
    )

    return {
        "total_celulas": total_cells,
        "total_parasitos": total_parasites,
        "parasitos_asignados": assigned_parasites,
        "parasitos_no_asignados": unassigned_parasites,
        "celulas_infectadas": infected_cells,
        "promedio_confianza_asignacion": float(assignment["mean_assignment_confidence"]),
        "promedio_confianza_asignaciones_confiables": float(
            assignment["mean_confident_assignment_confidence"]
        ),
        "promedio_parasitos_por_celula": avg_parasites_per_infected_cell,
        "parasitos_por_celula": parasites_per_cell.tolist(),
    }


def summarize_job(image_metrics: list[Dict[str, object]]) -> Dict[str, object]:
    """
    Agrega metricas a nivel job.
    """
    if not image_metrics:
        return {
            "imagenes_procesadas": 0,
            "total_celulas": 0,
            "total_parasitos": 0,
            "total_parasitos_asignados": 0,
            "total_parasitos_no_asignados": 0,
            "total_celulas_infectadas": 0,
        }

    total_cells = int(sum(int(m.get("total_celulas", 0)) for m in image_metrics))
    total_parasites = int(sum(int(m.get("total_parasitos", 0)) for m in image_metrics))
    total_assigned = int(sum(int(m.get("parasitos_asignados", 0)) for m in image_metrics))
    total_unassigned = int(sum(int(m.get("parasitos_no_asignados", 0)) for m in image_metrics))
    total_infected_cells = int(sum(int(m.get("celulas_infectadas", 0)) for m in image_metrics))

    return {
        "imagenes_procesadas": len(image_metrics),
        "total_celulas": total_cells,
        "total_parasitos": total_parasites,
        "total_parasitos_asignados": total_assigned,
        "total_parasitos_no_asignados": total_unassigned,
        "total_celulas_infectadas": total_infected_cells,
    }
