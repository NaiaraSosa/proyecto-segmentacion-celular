## **Configuración de entornos**

**Miniforge**
Instalador
- Linux: wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh 
- Windows: Desde este link *$https://github.com/conda-forge/miniforge/releases/latest$* descargar $Miniforge3-Windows-x86_64.exe$. 

Ejecutar: 
- Linux: $bash Miniforge3-Linux-x86_64.sh -p /<carpeta>$

conda init bash
conda deactivate
rm ~/Miniforge3-Linux-x86_64.sh

**Crear y activar entorno $segapp_env$**
conda create -p /<raiz-proyecto>/segapp_env python=3.10 -y
conda activate /rhoeql/lab/naiara/conda_envs/segapp_env
conda activate C:\Users\naiar\OneDrive\Escritorio\Unsam\ciencia-de-datos\proyecto\segapp_env

**Instalar app desde $pyproject.toml$**
pip install -U pip
pip install -e .

**Pyproyect.toml**
Qué hace: declara el proyecto y que necesitamos FastAPI + Uvicorn (servidor web), python-multipart (para subir archivos), jinja2 (para renderizar HTML).

## **Levantar APP**
Linux: uvicorn app.main:app --host 0.0.0.0 --port 8000
Windows: python -m uvicorn app.main:app --host 127.0.0.1 --port 8010


**Probar upload con curl**
curl -X POST "http://127.0.0.1:8000/upload" \
  -F "file=@/home/naiara/programa-segmentacion/tests/Snap-12879.tiff"
