# **Automatización de segmentación celular para imágenes microscópicas**

En el Instituto de Investigaciones Biotecnológicas, se está trabajando para hallar fármacos capaces de curar la Enfermedad de Chagas. Con este fin, una parte del proceso consiste en ensayos de fármacos experimentales, en cultivos de células infectadas con los parásitos causantes de la enfermedad. Se toman  imágenes microscópicas del cultivo de las células, previa y posteriormente a ser infectadas. 

Actualmente, la curación manual de imágenes (conteo y etiquetado de células) resulta demandante  en tiempo, por lo que se busca **entrenar y evaluar modelos de segmentación automática** para acelerar este proceso.  

## Objetivo
El objetivo principal de este proyecto es **automatizar las tareas de análisis de imágenes de microscopía**, con el fin de contar y etiquetar células, de manera precisa, rápida y reproducible. 

## Programa de Segmentación Celular

Aplicacion web en FastAPI para ejecutar un pipeline de segmentación de imágenes de microscopía.

## Requisitos

- Python 3.10
- Conda/Miniforge (recomendado)
- SO probado: Windows

## Instalación

1. Miniforge:

- Linux

```bash
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh 
bash Miniforge3-Linux-x86_64.sh -p /<carpeta>/miniforge3
```

- Windows:

Ingresar a: https://github.com/conda-forge/miniforge/releases/latest

Descargar `Miniforge3-Windows-x86_64.exe` y ejecutar `.exe`.


2. Crear entorno:

```bash
conda create -p C:\Users\naiar\OneDrive\Escritorio\Unsam\ciencia-de-datos\proyecto\segapp_env python=3.10 -y
conda create -p /rhoeql/lab/naiara/conda_envs/segapp_env python=3.10 -y
```

2. Activar entorno:

```bash
conda activate C:\Users\naiar\OneDrive\Escritorio\Unsam\ciencia-de-datos\proyecto\segapp_env
conda activate /rhoeql/lab/naiara/conda_envs/segapp_env
```

3. Instalar dependencias del proyecto `pyproject.toml`:

```bash
pip install -U pip
pip install -e .
pip install "tensorflow-cpu==2.15.*"
```

## Ejecutar la API

Desde la carpeta `programa-segmentacion`:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

URL local:

```text
http://127.0.0.1:8010
http://127.0.0.1:8000
```

## Variables de entorno

Se documentan en `.env.example`:

- `APP_HOST`
- `APP_PORT`
- `DATA_DIR`
- `UPLOADS_DIR`
- `OUTPUTS_DIR`
- `TEMP_DIR`
- `MAX_UPLOAD_MB`

## Estructura del proyecto

```text
app/
  api/         # Endpoints FastAPI
  core/        # Configuracion general
  pipeline/    # Logica de procesamiento
  services/    # Utilidades de jobs/archivos
  main.py      # Entrada de la app
data/
  uploads/     # Archivos subidos por job
  outputs/     # Resultados exportados por job
  temp/        # Temporales de procesamiento
```

## Flujo actual

1. Subir archivo (`/upload`).
2. Disparar procesamiento (`/process/{job_id}`).
3. Descargar resultados (`/download/{job_id}`).

## Troubleshooting rapido

- `WinError 10013`: usar otro puerto (ej. `8010`).
- `python` apunta a `WindowsApps`: activar `segapp_env` y volver a intentar.
- `uvicorn` no se reconoce: ejecutar con `python -m uvicorn ...`.

## Roadmap

- Integrar inference real con Cellpose y StarDist.
- Separar `runner.py` en etapas (io, preprocess, inference, postprocess, export).
- Agregar tests de API y pipeline.
- Agregar Dockerfile para entorno reproducible.

**Git**
```bash
git status
git add .
git commit -m "mensaje cambio"
git push
```

