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

    infection_rate = float(infected_cells / total_cells) if total_cells > 0 else 0.0
    avg_parasites_per_cell = float(total_parasites / total_cells) if total_cells > 0 else 0.0
    avg_parasites_per_infected_cell = (
        float(total_parasites / infected_cells) if infected_cells > 0 else 0.0
    )

    return {
        "total_cells": total_cells,
        "total_parasites": total_parasites,
        "infected_cells": int(infected_cells),
        "unassigned_parasites": int(unassigned_parasites),
        "infection_rate": infection_rate,
        "avg_parasites_per_cell": avg_parasites_per_cell,
        "avg_parasites_per_infected_cell": avg_parasites_per_infected_cell,
        "parasites_per_cell": parasites_per_cell.tolist(),
    }


def summarize_job(image_metrics: list[Dict[str, object]]) -> Dict[str, object]:
    """
    Agrega metricas a nivel job.
    """
    if not image_metrics:
        return {
            "images_processed": 0,
            "total_cells": 0,
            "total_parasites": 0,
            "total_infected_cells": 0,
            "mean_infection_rate": 0.0,
        }

    total_cells = int(sum(int(m.get("total_cells", 0)) for m in image_metrics))
    total_parasites = int(sum(int(m.get("total_parasites", 0)) for m in image_metrics))
    total_infected_cells = int(sum(int(m.get("infected_cells", 0)) for m in image_metrics))
    mean_infection_rate = float(np.mean([float(m.get("infection_rate", 0.0)) for m in image_metrics]))

    return {
        "images_processed": len(image_metrics),
        "total_cells": total_cells,
        "total_parasites": total_parasites,
        "total_infected_cells": total_infected_cells,
        "mean_infection_rate": mean_infection_rate,
    }
