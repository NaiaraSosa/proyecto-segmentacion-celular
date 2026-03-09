import json
import shutil
import time
import zipfile
from pathlib import Path
import numpy as np
#import tifffile as tiff
#import matplotlib.pyplot as plt
#from cellpose import models

from app.core.config import settings

IMAGE_EXTS = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}

# Cache del modelo (evita recargarlo por cada imagen)
_MODEL = None

#def _get_model():
#    global _MODEL
#    if _MODEL is None:
#        _MODEL = models.CellposeModel(gpu=True)
#    return _MODEL

#def _save_overlay_png(img: np.ndarray, mask: np.ndarray, out_png: Path) -> None:
#    """
#    Overlay simple: muestra la imagen y contornos de máscara.
#   """
#   out_png.parent.mkdir(parents=True, exist_ok=True)
#
#    # Si viene multi-canal o 3D, lo simplificamos a 2D para visualizar
#    if img.ndim == 3:
#        # casos comunes: (H,W,C) o (Z,H,W). Elegimos una heurística:
#       if img.shape[-1] in (3, 4):
#            img2d = img[..., 0]  # canal 0
#        else:
#            img2d = img[0, ...]  # primer slice
#    else:
#        img2d = img
#
#    plt.figure()
#    plt.imshow(img2d, cmap="gray")
#    # Contornos sobre labels > 0
#   plt.contour(mask > 0, levels=[0.5], linewidths=1)
#    plt.axis("off")
#    plt.tight_layout(pad=0)
#    plt.savefig(out_png, dpi=200, bbox_inches="tight", pad_inches=0)
#    plt.close()


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

    # 1) armar lista de imágenes a procesar
    if uploaded.suffix.lower() == ".zip":
        unzip_dir = job_temp_dir / "unzipped"
        if unzip_dir.exists():
            shutil.rmtree(unzip_dir)
        unzip_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(uploaded, "r") as zf:
            zf.extractall(unzip_dir)

        images = [p for p in unzip_dir.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
        images.sort(key=lambda p: str(p).lower())
        if not images:
            raise ValueError("El ZIP no contiene imágenes soportadas.")
    else:
        if uploaded.suffix.lower() not in IMAGE_EXTS:
            raise ValueError("Archivo no soportado. Subí una imagen o un ZIP con imágenes.")
        images = [uploaded]

    # 2) crear estructura de salida por imagen
    export_root = job_output_dir / f"job_{job_id}"
    images_root = export_root / "images"
    images_root.mkdir(parents=True, exist_ok=True)

    time.sleep(1)  # simula procesamiento

    for i, img_path in enumerate(images, start=1):
        img_id = f"{i:04d}"
        folder = images_root / f"{img_id}__{img_path.stem}"
        folder.mkdir(parents=True, exist_ok=True)

        # input
        shutil.copy2(img_path, folder / f"input{img_path.suffix.lower()}")

        # mask dummy
        (folder / "mask.tif").write_bytes(b"FAKE_MASK\n")

        # metrics dummy
        metrics = {"job_id": job_id, "image_id": img_id, "source_filename": img_path.name, "iou": 0.0, "dice": 0.0}
        (folder / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # 3) zip final
    zip_path = job_output_dir / f"results_{job_id}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in export_root.rglob("*"):
            if p.is_file():
                zf.write(p, arcname=str(p.relative_to(job_output_dir)))

    return zip_path