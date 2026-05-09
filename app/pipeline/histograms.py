from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np


def save_histogram(
    path: Path,
    parasites_per_cell: Iterable[int],
    title: str = "Parasitos por celula",
) -> None:
    values = [int(value) for value in parasites_per_cell if int(value) >= 0]

    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    fig, ax = plt.subplots(figsize=(8, 5), dpi=140)
    fig.patch.set_facecolor("#0d1220")
    ax.set_facecolor("#111728")

    if values:
        max_value = max(values)
        bins = np.arange(-0.5, max_value + 1.5, 1)
        ax.hist(values, bins=bins, color="#7da3ff", edgecolor="#edf2ff", linewidth=0.8)
        if max_value <= 25:
            ax.set_xticks(range(max_value + 1))
        else:
            ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=12))
        ax.set_xlim(-0.5, max_value + 0.5)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    else:
        ax.text(
            0.5,
            0.5,
            "Sin celulas detectadas",
            color="#edf2ff",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=14,
        )
        ax.set_xticks([])
        ax.set_yticks([])

    ax.set_title(title, color="#edf2ff", pad=14)
    ax.set_xlabel("Parásitos por celula", color="#c8d6fa", labelpad=10)
    ax.set_ylabel("Cantidad de células", color="#c8d6fa", labelpad=10)
    ax.tick_params(colors="#c8d6fa")
    ax.grid(axis="y", color="#2a3144", linewidth=0.8, alpha=0.8)

    for spine in ax.spines.values():
        spine.set_color("#2a3144")

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
