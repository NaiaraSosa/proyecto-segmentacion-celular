from __future__ import annotations
import os
import shutil
import zipfile
from pathlib import Path

import numpy as np
import tifffile
from openpyxl import Workbook
from scipy.ndimage import binary_erosion

from app.core.config import settings
from app.pipeline.cellpose import segment_cells
from app.pipeline.io import IMAGE_EXTS as IO_IMAGE_EXTS
from app.pipeline.io import load_image_2d
from app.pipeline.metrics import compute_metrics, summarize_job
from app.pipeline.previews import build_input_preview, build_instance_preview, save_preview
from app.pipeline.postprocess import filter_cells_by_area, filter_parasites_by_area, merge_parasites
from app.pipeline.stardist import segment_parasites

IMAGE_EXTS = set(IO_IMAGE_EXTS) | {".zip"}
CELL_MIN_AREA = int(os.getenv("CELL_MIN_AREA", "500"))
PARASITE_MAX_AREA = int(os.getenv("PARASITE_MAX_AREA", "500"))
PARASITE_ASSIGN_SIGMA = float(os.getenv("PARASITE_ASSIGN_SIGMA", "120"))
PARASITE_ASSIGN_THRESHOLD = float(os.getenv("PARASITE_ASSIGN_THRESHOLD", "0.5"))


def _resolve_input_images(uploaded: Path, job_temp_dir: Path) -> list[Path]:
    """
    Resuelve las imágenes de entrada desde un archivo subido.

    Si el archivo es una imagen individual (TIFF/CZI), la valida y devuelve en una lista.
    Si es un ZIP, lo descomprime en un directorio temporal, extrae todas las imágenes
    soportadas, las ordena alfabéticamente y las devuelve.

    Returns:
        Lista de rutas a las imágenes procesables.

    Raises:
        ValueError: Si el archivo no es soportado o el ZIP no contiene imágenes válidas.
    """
    # Caso 1: Archivo individual (no ZIP)
    if uploaded.suffix.lower() != ".zip":
        # Verificar que sea una extensión de imagen soportada
        if uploaded.suffix.lower() not in IO_IMAGE_EXTS:
            raise ValueError("Archivo no soportado. Subi una imagen TIFF/CZI o un ZIP con imagenes.")
        # Devolver la imagen como lista de un elemento
        return [uploaded]

    # Caso 2: Archivo ZIP - descomprimir y extraer imágenes
    unzip_dir = job_temp_dir / "unzipped"
    # Limpiar directorio si existe
    if unzip_dir.exists():
        shutil.rmtree(unzip_dir)
    unzip_dir.mkdir(parents=True, exist_ok=True)

    # Extraer todo el contenido del ZIP
    with zipfile.ZipFile(uploaded, "r") as zf:
        zf.extractall(unzip_dir)

    # Buscar recursivamente todas las imágenes con extensiones soportadas
    images = [p for p in unzip_dir.rglob("*") if p.is_file() and p.suffix.lower() in IO_IMAGE_EXTS]
    # Ordenar alfabéticamente por ruta completa (case-insensitive)
    images.sort(key=lambda p: str(p).lower())
    # Verificar que se encontraron imágenes
    if not images:
        raise ValueError("El ZIP no contiene imagenes soportadas (tif/tiff/czi).")

    return images

def _convert_to_tiff(img: np.ndarray) -> np.ndarray:
    """
    Convierte una imagen NumPy a formato uint16 para guardar como TIFF.

    Esta función normaliza todo a uint16 (0-65535) que es estándar para TIFF,
    permitiendo rango dinámico completo de 16 bits.

    Args:
        img: Array 2D NumPy, puede ser float o integer.

    Returns:
        Array 2D uint16 normalizado.
    """
    if np.issubdtype(img.dtype, np.floating):
        # Para floats: normalizar al rango completo de uint16
        img = np.nan_to_num(img, nan=0.0, posinf=0.0, neginf=0.0)
        vmin, vmax = float(img.min()), float(img.max())
        if vmax > vmin:
            img = ((img - vmin) / (vmax - vmin) * 65535.0).astype(np.uint16)
        else:
            img = np.zeros_like(img, dtype=np.uint16)
    elif img.dtype != np.uint16:
        # Para otros tipos: convertir directamente
        img = img.astype(np.uint16, copy=False)
    return img


def _write_metrics_excel(path: Path, summary: dict[str, object], image_metrics: list[dict[str, object]]) -> None:
    wb = Workbook()

    ws_summary = wb.active
    ws_summary.title = "Generales"
    ws_summary.append(
        [
            "job_id",
            "imagenes_procesadas",
            "total_celulas",
            "total_parasitos",
            "total_parasitos_asignados",
            "total_parasitos_no_asignados",
            "total_celulas_infectadas",
        ]
    )
    ws_summary.append(
        [
            summary.get("job_id", ""),
            int(summary.get("imagenes_procesadas", 0)),
            int(summary.get("total_celulas", 0)),
            int(summary.get("total_parasitos", 0)),
            int(summary.get("total_parasitos_asignados", 0)),
            int(summary.get("total_parasitos_no_asignados", 0)),
            int(summary.get("total_celulas_infectadas", 0)),
        ]
    )

    ws_images = wb.create_sheet("Por imagen")
    ws_images.append(
        [
            "job_id",
            "image_id",
            "source_filename",
            "total_celulas",
            "total_parasitos",
            "parasitos_asignados",
            "parasitos_no_asignados",
            "celulas_infectadas",
            "promedio_confianza_asignacion",
            "promedio_parasitos_por_celula",
            "parasitos_por_celula",
        ]
    )
    for m in image_metrics:
        ws_images.append(
            [
                m.get("job_id", ""),
                m.get("image_id", ""),
                m.get("source_filename", ""),
                int(m.get("total_celulas", 0)),
                int(m.get("total_parasitos", 0)),
                int(m.get("parasitos_asignados", 0)),
                int(m.get("parasitos_no_asignados", 0)),
                int(m.get("celulas_infectadas", 0)),
                float(m.get("promedio_confianza_asignacion", 0.0)),
                float(m.get("promedio_parasitos_por_celula", 0.0)),
                ";".join(str(x) for x in m.get("parasitos_por_celula", [])),
            ]
        )

    wb.save(path)


def _build_infected_overlay(
    preview: np.ndarray, 
    cells_lab: np.ndarray, 
    parasites_per_cell: list[int] | np.ndarray,
    border_width: int = 1
) -> np.ndarray:
    """
    Crea un overlay RGB marcando en rojo el contorno de células infectadas.

    Superpone marcas rojas sobre la preview de la imagen original para
    resaltar visualmente qué células contienen parásitos. Útil para
    verificación rápida de resultados.

    Args:
        preview_rgb: Preview RGB de la imagen original (Y, X, 3) uint8.
        cells_lab: Máscara de células con IDs únicos (Y, X) int32.
        parasites_per_cell: Lista/array con conteo de parásitos por célula.
            Índice i corresponde a célula con ID (i+1).

    Returns:
        Array RGB (Y, X, 3) uint8 con contornos rojos sobre células infectadas.
        Células no infectadas se ven normales, infectadas tienen borde rojo.
    """
    overlay = preview.copy()
    counts = np.asarray(parasites_per_cell, dtype=int)
    if counts.size == 0:
        return overlay

    infected_ids = np.where(counts > 0)[0] + 1
    if infected_ids.size == 0:
        return overlay

    infected_mask = np.isin(cells_lab, infected_ids)
    if not infected_mask.any():
        return overlay

    size = 2 * border_width + 1
    structure = np.ones((size, size), dtype=bool)
    eroded = binary_erosion(infected_mask, structure=structure, border_value=0)
    border = infected_mask & ~eroded
    overlay[border] = np.array([255, 0, 0], dtype=np.uint8)
    return overlay

def run_pipeline(job_id: str) -> tuple[Path, list[dict[str, object]]]:
    job_upload_dir = settings.uploads_dir / job_id
    job_output_dir = settings.outputs_dir / job_id
    job_temp_dir = settings.temp_dir / job_id

    job_output_dir.mkdir(parents=True, exist_ok=True)
    job_temp_dir.mkdir(parents=True, exist_ok=True)

    uploaded_files = [p for p in job_upload_dir.iterdir() if p.is_file()]
    if not uploaded_files:
        raise FileNotFoundError("No hay archivo subido para este job.")

    uploaded = uploaded_files[0]
    images = _resolve_input_images(uploaded, job_temp_dir)

    export_root = job_output_dir / f"job_{job_id}"
    images_root = export_root / "images"
    images_root.mkdir(parents=True, exist_ok=True)

    all_metrics: list[dict[str, object]] = []
    preview_items: list[dict[str, object]] = []

    for i, img_path in enumerate(images, start=1):
        img_id = f"{i:04d}"
        folder = images_root / f"{img_id}__{img_path.stem}"
        folder.mkdir(parents=True, exist_ok=True)

        img2d = load_image_2d(img_path)

        img_out = _convert_to_tiff(img2d)
        tifffile.imwrite(str(folder / "input.tiff"), img_out)

        preview = build_input_preview(img2d)
        save_preview(folder / "input_preview.png", preview)

        cells_lab = segment_cells(img2d)
        cells_lab = filter_cells_by_area(cells_lab, min_area=CELL_MIN_AREA)

        parasites_lab, _ = segment_parasites(img2d)
        parasites_lab = filter_parasites_by_area(parasites_lab, max_area=PARASITE_MAX_AREA)

        parasites_lab = merge_parasites(parasites_lab, merge_radius=2)

        tifffile.imwrite(str(folder / "cell_mask.tiff"), cells_lab.astype("uint16"))
        tifffile.imwrite(str(folder / "parasite_mask.tiff"), parasites_lab.astype("uint16"))
        save_preview(folder / "cell_mask_preview.png", build_instance_preview(cells_lab))
        save_preview(folder / "parasite_mask_preview.png", build_instance_preview(parasites_lab))

        metrics = {
            "job_id": job_id,
            "image_id": img_id,
            "source_filename": img_path.name,
            **compute_metrics(
                cells_lab,
                parasites_lab,
                assign_sigma=PARASITE_ASSIGN_SIGMA,
                assign_threshold=PARASITE_ASSIGN_THRESHOLD,
            ),
        }
        all_metrics.append(metrics)

        preview_items.append(
            {
                "title": folder.name,
                "folder_name": folder.name,
                "metrics": {
                    "total_celulas": int(metrics.get("total_celulas", 0)),
                    "total_parasitos": int(metrics.get("total_parasitos", 0)),
                    "celulas_infectadas": int(metrics.get("celulas_infectadas", 0)),
                    "parasitos_no_asignados": int(metrics.get("parasitos_no_asignados", 0)),
                    "promedio_parasitos_por_celula": int(round(metrics.get("promedio_parasitos_por_celula", 0.0))),
                    "parasitos_por_celula": metrics.get("parasitos_por_celula", []),
                },
            }
        )

        infected_overlay = _build_infected_overlay(
            preview=preview,
            cells_lab=cells_lab,
            parasites_per_cell=metrics.get("parasitos_por_celula", []), border_width=2
        )
        save_preview(folder / "infected_overlay.png", infected_overlay)

    summary = summarize_job(all_metrics)
    summary_row = {"job_id": job_id, **summary}
    _write_metrics_excel(export_root / "metrics.xlsx", summary_row, all_metrics)

    zip_path = job_output_dir / f"results_{job_id}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in export_root.rglob("*"):
            if p.is_file():
                zf.write(p, arcname=str(p.relative_to(job_output_dir)))

    return zip_path, preview_items
