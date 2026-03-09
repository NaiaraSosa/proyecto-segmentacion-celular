# entrada FASTAPI

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.core.config import ensure_dirs
from app.api.routes import router as api_router

app = FastAPI(title="Programa Segmentación")

app.include_router(api_router)

@app.on_event("startup")
def _startup():
    ensure_dirs()

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
      <head>
        <title>Programa Segmentación</title>
      </head>
      <body style="font-family: sans-serif; max-width: 720px; margin: 40px auto;">
        <h1>Programa Segmentación</h1>
        
        <h2>Subir imagen o ZIP</h2>

        <form action="/upload" enctype="multipart/form-data" method="post">
          <input type="file" name="file" required>
          <br><br>
          <button type="submit">Subir</button>
        </form>
        
      </body>
    </html>
    """