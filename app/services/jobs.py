# crea job_id, carpetas, estado

import uuid
from pathlib import Path
from app.core.config import settings


def create_job() -> str:
    """
    Crea un job_id único y sus carpetas asociadas.
    """
    job_id = str(uuid.uuid4())

    job_upload_dir = settings.uploads_dir / job_id
    job_output_dir = settings.outputs_dir / job_id

    job_upload_dir.mkdir(parents=True, exist_ok=True)
    job_output_dir.mkdir(parents=True, exist_ok=True)

    return job_id