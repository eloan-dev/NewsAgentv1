# importando librerías necesarias
import os
import sys
import csv
from fastapi import FastAPI, UploadFile, BackgroundTasks, Query, File
from fastapi.responses import JSONResponse,FileResponse
from pydantic import BaseModel
import csv
import json
from threading import Lock

# Bandera de control de las tareas de segundo plano y avance de procesamiento
processing_flag = False
processing_lock = Lock()

# Asegurarse de que el directorio 'lib' esté en el path para imports
project_root = os.path.dirname(os.path.abspath(__file__))
code_dir = os.path.join(project_root, "codigo")
if code_dir not in sys.path:
    sys.path.append(code_dir)

from codigo.notebook_utils import setup_environment
from codigo.main3 import run_pipeline

app = FastAPI(title="NewsAgent API")



#--------ENDPOINTS DE PDF-------------------
#---- upload pdf
@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Endpoint upload_pdf.
    Sube un archivo PDF al servidor y lo guarda temporalmente.

    Args:
        file (UploadFile): Archivo PDF enviado desde el cliente.

    Returns:
        dict: Un diccionario con el nombre del archivo guardado.
    """
    # Guarda el archivo temporalmente
    file_location = f"base/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())
    # Retorna el nombre o un ID para referencia posterior
    return {"filename": file.filename}


#-----process pdf
class ProcesarPDFRequest(BaseModel):
    filename: str
    prompt: str
    batchSize: int
    pauseSeconds: int

@app.post("/procesar_pdf/")
async def procesar_pdf(req: ProcesarPDFRequest, background_tasks: BackgroundTasks):
    """
    Procesa el PDF subido usando los parámetros personalizados y retorna el análisis en JSON.
    """

    global processing_flag

    # Ruta del archivo PDF subido
    file_path = os.path.join("base", req.filename + ".pdf")
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "Archivo no encontrado"})
    
    #ruta archivo json 
    json_path = os.path.join("output/clean", f"clean_{req.filename}.json")
    
    # Si ya existe el resultado, no proceses de nuevo
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content={
            "message": "Archivo ya procesado anteriormente.",
            "status": "ya_procesado",
            "data": data
        })
    else:
        with processing_lock:
            if processing_flag:
                return JSONResponse(
                    status_code=429,
                    content={"error": "Ya hay un procesamiento en curso. Por favor, espera unos minutos."}
                )
            processing_flag = True

        # Ejecutar el proceso en segundo plano
        background_tasks.add_task(ejecutar_procesamiento, req.filename)

        return JSONResponse(content={
            "message": "Procesamiento iniciado. Puedes consultar el resultado en unos minutos.",
            "status": "en_proceso"
        })
        

#----download markdown file
@app.get("/download_md/{filename}")
async def download_md(filename: str):
    md_path = os.path.join("output/clean", f"clean_{filename}.md")
    if not os.path.exists(md_path):
        return JSONResponse(status_code=404, content={"error": "Archivo .md no encontrado"})
    return FileResponse(md_path, media_type="text/markdown", filename=f"{filename}.md")


#---- send to URLs extracted
@app.get("/urls_extraidas/{namefile}")
async def urls_extraidas(namefile: str):
    """
    Devuelve la lista de URLs extraídas leyendo el archivo CSV correspondiente.
    La URL está en la segunda columna del CSV.
    """
    csv_path = os.path.join("input", "In", f"links_extracted_{namefile}.csv")
    if not os.path.exists(csv_path):
        return JSONResponse(status_code=404, content={"error": "Archivo CSV no encontrado"})
    try:
        urls = []
        with open(csv_path, newline='', encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            next(reader, None)  # Saltar encabezado
            for row in reader:
                if len(row) > 1 and row[1].startswith("http"):
                    urls.append(row[1])
        return JSONResponse(content={"urls": urls})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


#---Ejecución en segundo plano
def ejecutar_procesamiento(filename: str):
    global processing_flag
    try:
        setup_environment(project_root)
        run_pipeline(filename)

        #ejecucion terminada correctamente
        print(f"Procesamiento terminado para: {filename}")
    except Exception as e:
        print(f"[ERROR] Falló el procesamiento de {filename}: {e}")
    finally:
        with processing_lock:
            processing_flag = False

#---resultado pdf
@app.get("/resultado_pdf/{filename}")
async def resultado_pdf(filename: str):
    json_path = os.path.join("output/clean", f"clean_{filename}.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content=data)
    else:
        return JSONResponse(
            status_code=202, 
            content={"status": "en_proceso", "mensaje": "El procesamiento aún no ha terminado."}
        )


#----agregando CORS para permitir peticiones desde cualquier origen
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia esto a los dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#testeo
@app.get("/check_path/")
def check_path(path: str = Query(..., description="Ruta a verificar, por ejemplo: 'base'")):
    """
    Verifica si una ruta existe en el sistema de archivos.

    Args:
        path (str): Ruta relativa o absoluta a verificar.

    Returns:
        dict: Información sobre la existencia de la ruta y si es un directorio.
    """
    exists = os.path.exists(path)
    is_dir = os.path.isdir(path) if exists else False

    return JSONResponse(content={
        "path": path,
        "exists": exists,
        "is_directory": is_dir
    })