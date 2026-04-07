from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


_PALETTE = np.array(
    [
        [230, 57, 70],
        [29, 161, 242],
        [67, 170, 139],
        [244, 162, 97],
        [131, 56, 236],
        [255, 190, 11],
        [42, 157, 143],
        [239, 71, 111],
        [6, 214, 160],
        [17, 138, 178],
        [255, 127, 80],
        [144, 190, 109],
    ],
    dtype=np.uint8,
)


def _apply_viridis_colormap(gray: np.ndarray) -> np.ndarray:
    """
    Aplica un colormap tipo viridis a una imagen de una sola banda.

    El resultado es un array RGB uint8 que mapea valores de intensidad
    en [0, 255] a una escala de color similar a viridis.
    """
    x = gray.astype(np.float32) / 255.0
    r = np.interp(x, [0.0, 0.25, 0.5, 0.75, 1.0], [0.267, 0.229, 0.127, 0.369, 0.993])
    g = np.interp(x, [0.0, 0.25, 0.5, 0.75, 1.0], [0.004, 0.322, 0.569, 0.788, 0.906])
    b = np.interp(x, [0.0, 0.25, 0.5, 0.75, 1.0], [0.329, 0.545, 0.550, 0.382, 0.143])
    rgb = np.stack([r, g, b], axis=-1)
    return (np.clip(rgb, 0.0, 1.0) * 255).astype(np.uint8)


def build_input_preview(img2d: np.ndarray, colormap: str | None = None) -> np.ndarray:
    """
    Crea una preview RGB desde una imagen 2D monocromática.

    Por defecto crea una preview en escala de grises, pero también puede usar
    un colormap tipo viridis para mejorar la visualización.

    Args:
        img2d: Array 2D NumPy (Y, X) con valores de intensidad.
        colormap: Nombre del colormap a aplicar. Soporta None o 'viridis'.

    Returns:
        Array RGB uint8 (Y, X, 3).

    Notes:
        - Ajuste de contraste: Usa percentiles 1-99 para ignorar outliers
        - Normalización: Escala al rango 0-255
        - Si colormap='viridis', usa una paleta de color perceptualmente agradable
    """
    x = img2d.astype(np.float32, copy=False)
    p1, p99 = np.percentile(x, [1, 99])
    if p99 > p1:
        x = np.clip((x - p1) / (p99 - p1), 0.0, 1.0)
    else:
        x = np.zeros_like(x, dtype=np.float32)
    gray = (x * 255).astype(np.uint8)

    if colormap == "viridis":
        return _apply_viridis_colormap(gray)

    return np.stack([gray, gray, gray], axis=-1)


def build_instance_preview(labels: np.ndarray) -> np.ndarray:
    """
    Crea una preview RGB coloreada desde máscaras de segmentación.

    Convierte máscaras con IDs únicos (cada instancia tiene un número)
    en una imagen RGB donde cada instancia tiene un color único.
    Útil para visualizar resultados de segmentación de células/parásitos.

    Args:
        labels: Array 2D int con IDs de instancias (0 = fondo, 1,2,3... = objetos).

    Returns:
        Array RGB uint8 (Y, X, 3) con colores asignados por instancia.

    Notes:
        - Usa paleta de 12 colores predefinidos
        - Colores se repiten cíclicamente: instancia N usa color N % 12
        - Fondo (ID=0) permanece negro
        - Facilita identificación visual de objetos segmentados
    """
    if labels.size == 0:
        return np.zeros((1, 1, 3), dtype=np.uint8)

    h, w = labels.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)

    positive = labels > 0
    if not positive.any():
        return rgb

    color_idx = labels[positive] % len(_PALETTE)
    rgb[positive] = _PALETTE[color_idx]
    return rgb


def save_preview(path: Path, rgb: np.ndarray) -> None:
    Image.fromarray(rgb, mode="RGB").save(path)
