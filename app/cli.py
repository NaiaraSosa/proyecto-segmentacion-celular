from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from app.core.config import ensure_dirs, settings

app = typer.Typer(
    name="segmentacion",
    help="Procesa imágenes de microscopía desde consola o levanta la webapp.",
    no_args_is_help=True,
)


def _default_job_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _validate_job_id(job_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", job_id):
        raise typer.BadParameter("Usa solo letras, numeros, guiones, guion bajo o punto.")
    return job_id


@app.command("process")
def process_images(
    input_path: Annotated[
        Path,
        typer.Argument(
            help="Imagen, ZIP o directorio con imagenes .tif, .tiff o .czi.",
        ),
    ],
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Directorio raiz donde se guarda la carpeta del procesamiento.",
        ),
    ] = settings.outputs_dir,
    temp_dir: Annotated[
        Path | None,
        typer.Option(
            "--temp-dir",
            help="Directorio raiz para temporales. Por defecto se usa <output>/.temp.",
        ),
    ] = None,
    job_id: Annotated[
        str | None,
        typer.Option(
            "--job-id",
            help="Nombre del job. Si no se indica, se usa una marca de tiempo.",
        ),
    ] = None,
) -> None:
    run_id = _validate_job_id(job_id or _default_job_id())
    input_path = input_path.expanduser().resolve()
    output_root = output_dir.expanduser().resolve()
    job_output_dir = output_root / run_id
    job_temp_dir = (temp_dir.expanduser().resolve() / run_id) if temp_dir else output_root / ".temp" / run_id

    if not input_path.exists():
        raise typer.BadParameter(f"No existe la entrada: {input_path}")

    if output_root.exists() and not output_root.is_dir():
        raise typer.BadParameter(f"La salida debe ser un directorio: {output_root}")

    if job_output_dir.exists() and any(job_output_dir.iterdir()):
        raise typer.BadParameter(
            f"La carpeta del job ya existe y no esta vacia: {job_output_dir}. "
            "Usa otro --job-id o borra/mueve esos resultados."
        )

    try:
        from app.pipeline.runner import run_pipeline_from_input

        zip_path, preview_items, _summary_metrics = run_pipeline_from_input(
            input_path=input_path,
            job_output_dir=job_output_dir,
            job_temp_dir=job_temp_dir,
            job_id=run_id,
        )
    except Exception as exc:
        typer.secho(f"Error procesando imagenes: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.secho("Procesamiento terminado.", fg=typer.colors.GREEN)
    typer.echo(f"Job: {run_id}")
    typer.echo(f"Imagenes procesadas: {len(preview_items)}")
    typer.echo(f"Salida: {job_output_dir}")
    typer.echo(f"ZIP: {zip_path}")


@app.command("web")
def run_webapp(
    host: Annotated[
        str,
        typer.Option("--host", help="Host donde se levanta la webapp."),
    ] = settings.app_host,
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Puerto donde se levanta la webapp."),
    ] = settings.app_port,
    reload: Annotated[
        bool,
        typer.Option("--reload", help="Recargar automáticamente durante desarrollo."),
    ] = False,
) -> None:
    ensure_dirs()

    import uvicorn

    uvicorn.run("app.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
