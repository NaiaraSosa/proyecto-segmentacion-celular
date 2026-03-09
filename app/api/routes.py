from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
import shutil

from app.core.config import settings
from app.pipeline.runner import run_pipeline
from app.services.jobs import create_job

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


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

    return templates.TemplateResponse(
        "processed.html",
        {
            "request": request,
            "job_id": job_id,
            "zip_name": zip_path.name,
        },
    )


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
