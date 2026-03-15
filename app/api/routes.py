import csv
import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.pipeline.runner import run_pipeline
from app.services.jobs import create_job

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
PREVIEW_FILES = {"input_preview.png", "cell_mask_preview.png", "parasite_mask_preview.png"}


def _read_metrics(folder: Path) -> dict[str, object]:
    csv_path = folder / "metrics.csv"
    if not csv_path.exists():
        return {}

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        row = next(csv.DictReader(f), None)

    if row is None:
        return {}

    return {
        "total_celulas": int(row.get("total_celulas") or 0),
        "total_parasitos": int(row.get("total_parasitos") or 0),
        "celulas_infectadas": int(row.get("celulas_infectadas") or 0),
        "parasitos_no_asignados": int(row.get("parasitos_no_asignados") or 0),
    }


def _build_preview_items(job_id: str) -> list[dict[str, object]]:
    images_root = settings.outputs_dir / job_id / f"job_{job_id}" / "images"
    if not images_root.exists():
        return []

    items: list[dict[str, object]] = []
    folders = sorted([p for p in images_root.iterdir() if p.is_dir()], key=lambda p: p.name.lower())
    for folder in folders:
        items.append(
            {
                "title": folder.name,
                "input_url": f"/preview/{job_id}/{folder.name}/input_preview.png",
                "cell_url": f"/preview/{job_id}/{folder.name}/cell_mask_preview.png",
                "parasite_url": f"/preview/{job_id}/{folder.name}/parasite_mask_preview.png",
                "metrics": _read_metrics(folder),
            }
        )
    return items


@router.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Archivo invalido")

    job_id = create_job()
    job_upload_dir = settings.uploads_dir / job_id
    file_path = job_upload_dir / file.filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "job_id": job_id,
            "filename": file.filename,
        },
    )


@router.post("/process/{job_id}")
def process_job(request: Request, job_id: str):
    zip_path = run_pipeline(job_id)
    preview_items = _build_preview_items(job_id)

    return templates.TemplateResponse(
        "processed.html",
        {
            "request": request,
            "job_id": job_id,
            "zip_name": zip_path.name,
            "preview_items": preview_items,
        },
    )


@router.get("/preview/{job_id}/{image_folder}/{filename}")
def get_preview(job_id: str, image_folder: str, filename: str):
    if filename not in PREVIEW_FILES:
        raise HTTPException(status_code=404, detail="Preview no encontrado.")

    images_root = settings.outputs_dir / job_id / f"job_{job_id}" / "images"
    root_resolved = images_root.resolve()
    target = (images_root / image_folder / filename).resolve()
    if root_resolved not in target.parents or not target.exists():
        raise HTTPException(status_code=404, detail="Preview no encontrado.")

    return FileResponse(path=str(target), media_type="image/png")


@router.get("/download/{job_id}")
def download_results(job_id: str):
    zip_path = settings.outputs_dir / job_id / f"results_{job_id}.zip"

    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="No hay resultados para descargar. Ya procesaste el job?")

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"results_{job_id}.zip",
    )
