from __future__ import annotations
from typing import Dict
import numpy as np
from app.pipeline.postprocess import conteo_infeccion


def compute_metrics(cells_lab: np.ndarray, parasites_lab: np.ndarray) -> Dict[str, object]:
    """
    Calcula metricas principales por imagen a partir de mascaras de instancias.
    """
    total_cells = int(cells_lab.max()) if cells_lab.size else 0
    total_parasites = int(parasites_lab.max()) if parasites_lab.size else 0

    infected_cells, parasites_per_cell, unassigned_parasites = conteo_infeccion(cells_lab, parasites_lab)

    avg_parasites_per_infected_cell = (
        float(total_parasites / infected_cells) if infected_cells > 0 else 0.0
    )

    return {
        "total_celulas": total_cells,
        "total_parasitos": total_parasites,
        "celulas_infectadas": int(infected_cells),
        "parasitos_no_asignados": int(unassigned_parasites),
        "parasitos_por_celula": parasites_per_cell.tolist(),
        "promedio_parasitos_por_celula": avg_parasites_per_infected_cell,
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
            "total_celulas_infectadas": 0,
        }

    total_cells = int(sum(int(m.get("total_celulas", 0)) for m in image_metrics))
    total_parasites = int(sum(int(m.get("total_parasitos", 0)) for m in image_metrics))
    total_infected_cells = int(sum(int(m.get("celulas_infectadas", 0)) for m in image_metrics))

    return {
        "imagenes_procesadas": len(image_metrics),
        "total_celulas": total_cells,
        "total_parasitos": total_parasites,
        "total_celulas_infectadas": total_infected_cells,
    }
