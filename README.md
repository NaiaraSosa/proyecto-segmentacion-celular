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

3. Activar entorno:

```bash
conda activate C:\Users\naiar\OneDrive\Escritorio\Unsam\ciencia-de-datos\proyecto\segapp_env
conda activate /rhoeql/lab/naiara/conda_envs/segapp_env
```

4. Instalar dependencias del proyecto `pyproject.toml`:

```bash
pip install -U pip
pip install -e .
pip install "tensorflow-cpu==2.15.*"
```

## Ejecutar la API

Desde la carpeta `proyecto-segmentacion-celular`:

```bash
export CELL_MIN_AREA=500
export PARASITE_MAX_AREA=400
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

URL local:

```text
http://127.0.0.1:8010
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
- `CELL_MIN_AREA` (default: `500`)
- `PARASITE_MAX_AREA` (default: `450`)

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

1. Carga de imagen (`.tif/.tiff/.czi`) desde archivo suelto o ZIP.
2. Segmentacion de células con Cellpose.
3. Filtro de células por área mínima (`CELL_MIN_AREA`).
4. Segmentación de parásitos con StarDist.
5. Filtro de parásitos por área máxima (`PARASITE_MAX_AREA`).
6. Merge de parásitos cercanos para reducir doble conteo.
7. Asignación parasito -> célula (solape, o celula más cercana si no hay solape).
8. Cálculo de métricas y export de resultados.

## Métricas exportadas ```(metrics.json)```
- total_celulas: número total de células detectadas.
- total_parasitos: número total de parásitos detectados.
- celulas_infectadas: células con al menos un parásito asignado.
- parasitos_no_asignados: cantidad de parásitos que no pudieron asignarse a ninguna célula.
- parasitos_por_celula = cantidad de parásitos asignados por célula.¨

## Estructura del ZIP de salida

Por cada imagen:
- input.<ext>: imagen original.
- input_preview.png: vista normalizada para inspección visual.
- cell_mask.tif: máscara de instancias de células (Cellpose).
- parasite_mask.tif: máscara de instancias de parásitos (StarDist).
- metrics.json: métricas por imagen.

A nivel job:
- summary.json: agregados de todo el lote.
- results_<job_id>.zip: paquete final de resultados.

**Git**
```bash
git status
git add .
git commit -m "mensaje cambio"
git push
```

