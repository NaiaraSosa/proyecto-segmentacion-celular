from __future__ import annotations

import csv
import os
import shutil
import zipfile
from pathlib import Path

import numpy as np
import matplotlib.cm as cm 
import tifffile
from PIL import Image
from scipy.ndimage import binary_erosion

from app.core.config import settings
from app.pipeline.cellpose import segment_cells
from app.pipeline.io import IMAGE_EXTS as IO_IMAGE_EXTS
from app.pipeline.io import load_image_2d
from app.pipeline.metrics import compute_metrics, summarize_job
from app.pipeline.postprocess import filter_cells_by_area, filter_parasites_by_area, merge_parasites
from app.pipeline.stardist import segment_parasites

IMAGE_EXTS = set(IO_IMAGE_EXTS) | {".zip"}
CELL_MIN_AREA = int(os.getenv("CELL_MIN_AREA", "500"))
PARASITE_MAX_AREA = int(os.getenv("PARASITE_MAX_AREA", "500"))


def _resolve_input_images(uploaded: Path, job_temp_dir: Path) -> list[Path]:
    if uploaded.suffix.lower() != ".zip":
        if uploaded.suffix.lower() not in IO_IMAGE_EXTS:
            raise ValueError("Archivo no soportado. Subi una imagen TIFF/CZI o un ZIP con imagenes.")
        return [uploaded]

    unzip_dir = job_temp_dir / "unzipped"
    if unzip_dir.exists():
        shutil.rmtree(unzip_dir)
    unzip_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(uploaded, "r") as zf:
        zf.extractall(unzip_dir)

    images = [p for p in unzip_dir.rglob("*") if p.is_file() and p.suffix.lower() in IO_IMAGE_EXTS]
    images.sort(key=lambda p: str(p).lower())
    if not images:
        raise ValueError("El ZIP no contiene imagenes soportadas (tif/tiff/czi).")

    return images

def _write_csv(path: Path, row: dict[str, object], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)

def _metrics_to_csv_row(metrics: dict[str, object]) -> dict[str, object]:
    row = dict(metrics)
    row["parasitos_por_celula"] = ";".join(str(x) for x in row.get("parasitos_por_celula", []))
    return row


def _build_infected_overlay(
    preview_rgb: np.ndarray, cells_lab: np.ndarray, parasites_per_cell: list[int] | np.ndarray
) -> np.ndarray:
    """
    Crea un overlay RGB marcando en rojo el contorno de celulas infectadas.
    """
    overlay = preview_rgb.copy()
    counts = np.asarray(parasites_per_cell, dtype=int)
    if counts.size == 0:
        return overlay

    infected_ids = np.where(counts > 0)[0] + 1
    if infected_ids.size == 0:
        return overlay

    infected_mask = np.isin(cells_lab, infected_ids)
    if not infected_mask.any():
        return overlay

    # Solo dibuja borde para conservar visibilidad del fondo.
    eroded = binary_erosion(infected_mask, structure=np.ones((3, 3), dtype=bool), border_value=0)
    border = infected_mask & ~eroded
    overlay[border] = np.array([255, 0, 0], dtype=np.uint8)
    return overlay


def run_pipeline(job_id: str) -> Path:
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

    for i, img_path in enumerate(images, start=1):
        img_id = f"{i:04d}"
        folder = images_root / f"{img_id}__{img_path.stem}"
        folder.mkdir(parents=True, exist_ok=True)

        img2d = load_image_2d(img_path)

        # imagen de entrada convertida a tiff
        img_out = np.asarray(img2d)
        if np.issubdtype(img_out.dtype, np.floating):
            img_out = np.nan_to_num(img_out, nan=0.0, posinf=0.0, neginf=0.0)
            vmin, vmax = float(img_out.min()), float(img_out.max())
            if vmax > vmin:
                img_out = ((img_out - vmin) / (vmax - vmin) * 65535.0).astype(np.uint16)
            else:
                img_out = np.zeros_like(img_out, dtype=np.uint16)
        elif img_out.dtype != np.uint16:
            img_out = img_out.astype(np.uint16, copy=False)

        tifffile.imwrite(str(folder / "input.tif"), img_out)

        # preview PNG para visualizacion
        x = img2d.astype(np.float32, copy=False)
        p1, p99 = np.percentile(x, [1, 99])
        if p99 > p1:
            x = np.clip((x - p1) / (p99 - p1), 0, 1)
        else:
            x = np.zeros_like(x, dtype=np.float32)

        preview_gray = (x * 255).astype(np.uint8)
        preview_rgb = (cm.get_cmap("viridis")(preview_gray / 255.0)[..., :3] * 255).astype(np.uint8)
        Image.fromarray(preview_rgb, mode="RGB").save(folder / "preview.png")

        cells_lab = segment_cells(img2d)
        cells_lab = filter_cells_by_area(cells_lab, min_area=CELL_MIN_AREA)

        parasites_lab, _ = segment_parasites(img2d)
        parasites_lab = filter_parasites_by_area(parasites_lab, max_area=PARASITE_MAX_AREA)

        parasites_lab = merge_parasites(parasites_lab, merge_radius=2)

        tifffile.imwrite(str(folder / "cell_mask.tif"), cells_lab.astype("uint16"))
        tifffile.imwrite(str(folder / "parasite_mask.tif"), parasites_lab.astype("uint16"))

        metrics = {
            "job_id": job_id,
            "image_id": img_id,
            "source_filename": img_path.name,
            **compute_metrics(cells_lab, parasites_lab),
        }
        all_metrics.append(metrics)

        infected_overlay = _build_infected_overlay(
            preview_rgb=preview_rgb,
            cells_lab=cells_lab,
            parasites_per_cell=metrics.get("parasitos_por_celula", []),
        )
        Image.fromarray(infected_overlay, mode="RGB").save(folder / "infected_overlay.png")

        metrics_row = _metrics_to_csv_row(metrics)
        _write_csv(
            folder / "metrics.csv", 
            metrics_row, 
            fieldnames=[
                "job_id",
                "image_id",
                "source_filename",
                "total_celulas",
                "total_parasitos",
                "celulas_infectadas",
                "parasitos_no_asignados",
                "parasitos_por_celula",
            ]
        )

    summary = summarize_job(all_metrics)
    summary_row = {"job_id": job_id, **summary}
    _write_csv(
        export_root / "summary.csv",
        summary_row,
        fieldnames=[
            "job_id",
            "imagenes_procesadas",
            "total_celulas",
            "total_parasitos",
            "total_celulas_infectadas",
        ]
    )

    zip_path = job_output_dir / f"results_{job_id}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in export_root.rglob("*"):
            if p.is_file():
                zf.write(p, arcname=str(p.relative_to(job_output_dir)))

    return zip_path
