from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from app.pipeline.runner import run_pipeline
from pathlib import Path
import shutil

from app.services.jobs import create_job
from app.core.config import settings

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Validación básica
    if not file.filename:
        raise HTTPException(status_code=400, detail="Archivo inválido")

    job_id = create_job()

    job_upload_dir = settings.uploads_dir / job_id
    file_path = job_upload_dir / file.filename

    # Guardar archivo
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return HTMLResponse(f"""
        <html>
        <body style="font-family: sans-serif; max-width: 720px; margin: 40px auto;">
            <h2>Archivo subido correctamente ✅</h2>
            <p><strong>Job ID:</strong> {job_id}</p>

            <p><strong>Archivo:</strong> {file.filename}</p>

            <form action="/process/{job_id}" method="post" style="margin-top: 16px;">
            <button type="submit">Procesar</button>
            </form>

            <a href="/">Volver</a>
        </body>
        </html>
    """)

@router.post("/process/{job_id}", response_class=HTMLResponse)
def process_job(job_id:str):
    # Corre pipeline fake y genera results.zip
    zip_path = run_pipeline(job_id)

    return HTMLResponse(f"""
    <html>
      <body style="font-family: sans-serif; max-width: 720px; margin: 40px auto;">
        <h2>Procesamiento listo ✅</h2>
        <p><strong>Job ID:</strong> {job_id}</p>
        <p><a href="/download/{job_id}">Descargar resultados (ZIP)</a></p>
        <p><a href="/">Volver</a></p>
      </body>
    </html>
    """)

@router.get("/download/{job_id}")
def download_results(job_id: str):
    zip_path = settings.outputs_dir / job_id / f"results_{job_id}.zip"

    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="No hay resultados para descargar. ¿Ya procesaste el job?")

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"results_{job_id}.zip",
    )
