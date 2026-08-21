# **Herramienta automatizada para la segmentación y cuantificación de cultivos infectados**

En el Instituto de Investigaciones Biotecnológicas, se está trabajando para hallar fármacos capaces de curar la Enfermedad de Chagas. Con este fin, una parte del proceso consiste en ensayos de fármacos experimentales, en cultivos de células infectadas con los parásitos causantes de la enfermedad. Se toman  imágenes microscópicas del cultivo de las células, previa y posteriormente a ser infectadas. 

Actualmente, la curación manual de imágenes (conteo y etiquetado de células) resulta demandante  en tiempo, por lo que se busca **desarrollar una herramienta automatizada basada en modelos de segmentación automática**, capaz de acelerar este proceso.  

## Objetivo
El objetivo principal de este proyecto es **automatizar las tareas de análisis de imágenes de microscopía**, con el fin de cuantificar y etiquetar células, de manera precisa, rápida y reproducible. 

## Programa de segmentación selular

Aplicacion web en FastAPI para ejecutar un pipeline de segmentación de imágenes de microscopía.

## Requisitos

- Python 3.10
- Conda/Miniforge (recomendado)

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

2. Crear entorno conda con Python 3.10:

Especificar correctamente la ruta donde se desea crear el entorno:

```bash
conda create -p /ruta/a/conda_envs/segapp_env python=3.10 -y
conda activate /ruta/a/conda_envs/segapp_env
```

3. Instalar dependencias del proyecto `pyproject.toml`:

```bash
pip install -U pip
pip install -e .
pip uninstall -y torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

> Nota: el proyecto fija `numpy>=1.26,<2` porque TensorFlow 2.15/StarDist/CSBDeep no son compatibles con NumPy 2.x. Si `pip install -e .` actualiza NumPy a 2.x, volver a ejecutar `pip install -e .` desde esta carpeta lo baja a una versión compatible.

## Ejecutar el programa

La herramienta se puede usar de dos formas:
- desde consola, para procesar imágenes directamente con comandos.
- desde la webapp, para usar una interfaz visual en el navegador.

Para ver los comandos disponibles y sus opciones:

```bash
segmentacion --help 
```

Para ver las opciones de cada modo:
```bash
segmentacion process --help 
segmentacion web --help 
```

### Uso por consola

Procesar una imagen, un ZIP o un directorio local con imágenes. Ejemplo de uso indicando carpeta de salida e identificador del experimento:

```bash
segmentacion process ./test-imgs --output ./data/outputs --job-id experimento_01
```

En este caso --job-id permite asignarle un nombre al procesamiento. 

La entrada puede ser:

- una imagen `.tif`, `.tiff` o `.czi`.
- un `.zip` con imágenes soportadas.
- un directorio con imágenes soportadas, buscando recursivamente en subcarpetas.

Nota importante: el comando preprocess todavía no puede utilizarse!

## Uso de la webapp

Es útil para probar imágenes y revisar resultados. Desde la carpeta del proyecto ejecutar:

```bash
segmentacion web --host 127.0.0.1 --port 8010
```

Luego abrir en el navegador con la URL local:

```text
http://127.0.0.1:8010
```

## Estructura del proyecto

```text
app/
  api/         # Endpoints FastAPI
  core/        # Configuracion general
  pipeline/    # Logica de procesamiento
  services/    # Utilidades de jobs/archivos
  cli.py       # Entrada Typer para linea de comandos
  main.py      # Entrada de la app
data/
  uploads/     # Archivos subidos por job
  outputs/     # Resultados exportados por job
  temp/        # Temporales de procesamiento
```

## Flujo actual del procesamiento

1. Carga de imagen (`.tif/.tiff/.czi`) desde archivo suelto, ZIP o directorio.
2. Segmentacion de células con Cellpose.
3. Filtro de células por área mínima (`CELL_MIN_AREA`) y elongación máxima (`CELL_MAX_ELONGATION`).
4. Segmentación de parásitos con StarDist.
5. Filtro de parásitos por área máxima (`PARASITE_MAX_AREA`).
6. Merge de parásitos cercanos para reducir doble conteo.
7. Asignación parasito -> célula por solape y proximidad, y clusters en una segunda instancia.
8. Cálculo de métricas y export de resultados.

## Métricas exportadas

El ZIP incluye dos CSV principales:

- `metricas_generales.csv`: resumen del procesamiento completo.
- `metricas_por_imagen.csv`: una fila por imagen procesada.

Columnas principales:

- total_celulas: número total de células detectadas.
- total_parasitos: número total de parásitos detectados.
- celulas_infectadas: células con al menos un parásito asignado.
- parasitos_no_asignados: cantidad de parásitos que no pudieron asignarse a ninguna célula.
- parasitos_por_celula = cantidad de parásitos asignados por célula.

## Estructura del ZIP de salida

Por cada imagen:
- input.tiff: imagen original convertida a TIFF.
- cell_mask.tiff: máscara de instancias de células.
- parasite_mask.tiff: máscara de instancias de parásitos.
- infected_overlay: imagen original con células infectadas marcadas en rojo.

Por cada experimento:
- metricas_generales.csv: métricas generales del procesamiento.
- metricas_por_imagen.csv: métricas por imagen.
- histograma_global_global_parasitos_por_celula: distribución de los parásitos por célula a lo largo de todas las imágenes. 



