from __future__ import annotations
from pathlib import Path
from typing import Union
import numpy as np
import tifffile
from czifile import CziFile


PathLike = Union[str, Path]
IMAGE_EXTS = {".tif", ".tiff", ".czi"}

def load_image(path: PathLike) -> np.ndarray:
    """Carga imagen TIFF/CZI y devuelve array numpy crudo."""
    p = Path(path)
    ext = p.suffix.lower()

    if ext not in IMAGE_EXTS:
        raise ValueError(f"Extension no soportada: {ext}")

    if ext in {".tif", ".tiff"}:
        return tifffile.imread(str(p))

    if ext == ".czi":
        with CziFile(str(p)) as czi:
            return czi.asarray()

    raise ValueError(f"No se pudo cargar el archivo: {p}")

def extract_2d_frame(
    arr: np.ndarray,
    channel: int = 0,
    z: int = 0,
    t: int = 0,
) -> np.ndarray:
    """
    Intenta obtener una imagen 2D usable desde arrays con dimensiones variadas.
    """
    x = np.asarray(arr)
    x = np.squeeze(x)

    if x.ndim == 2:
        return x

    if x.ndim == 3:
        # (Y, X, C)
        if x.shape[-1] <= 4:
            return x[:, :, channel if channel < x.shape[-1] else 0]
        # (C, Y, X)
        if x.shape[0] <= 4:
            return x[channel if channel < x.shape[0] else 0, :, :]
        # (Z, Y, X) o similar
        return x[z if z < x.shape[0] else 0, :, :]

    # Para ndim >= 4: recorta ejes "extra" al índice 0 hasta llegar a 3D o 2D
    while x.ndim > 3:
        x = x[0]

    return extract_2d_frame(x, channel=channel, z=z, t=t)


def load_image_2d(path: PathLike) -> np.ndarray:
    """Carga archivo y devuelve frame 2D listo para pipeline."""
    raw = load_image(path)
    img2d = extract_2d_frame(raw)
    return img2d