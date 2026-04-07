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


def build_input_preview(img2d: np.ndarray) -> np.ndarray:
    """
    Crea una preview RGB en escala de grises desde una imagen 2D monocromática.

    Diseñado para visualizar imágenes de microscopía que son inherentemente
    monocromáticas (fluorescencia, brightfield) pero necesitan ser mostradas
    como RGB para compatibilidad con formatos de imagen estándar.

    Args:
        img2d: Array 2D NumPy (Y, X) con valores de intensidad.

    Returns:
        Array RGB uint8 (Y, X, 3) con los 3 canales idénticos (escala de grises).

    Notes:
        - Ajuste de contraste: Usa percentiles 1-99 para ignorar outliers
        - Normalización: Escala al rango 0-255
        - RGB: Crea 3 canales idénticos para formato RGB estándar
    """
    x = img2d.astype(np.float32, copy=False)
    p1, p99 = np.percentile(x, [1, 99])
    if p99 > p1:
        x = np.clip((x - p1) / (p99 - p1), 0.0, 1.0)
    else:
        x = np.zeros_like(x, dtype=np.float32)
    gray = (x * 255).astype(np.uint8)
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
