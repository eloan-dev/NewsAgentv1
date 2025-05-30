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
#---Ejecución en segundo plano
def ejecutar_procesamiento(req: ProcesarPDFRequest):
    global processing_flag
    try:
        setup_environment(project_root)
        run_pipeline(req.filename)
        print("Ejecución terminada exitosamente") #----------TEST
    except Exception as e:
        print(f"[ERROR] Falló el procesamiento de {req.filename}: {e}")
    finally:
        with processing_lock:
            processing_flag = False

@app.post("/procesar_pdf/")
async def procesar_pdf(req: ProcesarPDFRequest, background_tasks: BackgroundTasks):
    """
    Procesa el PDF subido usando los parámetros personalizados y retorna el análisis en JSON.
    """
    print(f"[INFO] Recibido request para procesar: {req.filename}") #---------test

    global processing_flag

    # Ruta del archivo PDF subido
    file_path = os.path.join("base", req.filename + ".pdf")
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "Archivo no encontrado"})
    
    print("buscando archivo json en output/clean") #----test
    #ruta archivo json 
    json_path = os.path.join("output/clean", f"clean_{req.filename}.json")
    
    # Si ya existe el resultado, no proceses de nuevo
    if os.path.exists(json_path):
        print("ingresando a ya procesado") #----test
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content={
            "message": "Archivo ya procesado anteriormente.",
            "status": "ya_procesado",
            "data": data
        })
   
    with processing_lock:
        print("ingresando a ver bandera") #----test
        if processing_flag:
            return JSONResponse(
                status_code=429,
                content={"error": "Ya hay un procesamiento en curso. Por favor, espera unos minutos."}
            )
        processing_flag = True

    # Ejecutar el proceso en segundo plano
    print("ingresando a ejecutar procesamiento en segundo plano")
    background_tasks.add_task(ejecutar_procesamiento, req)

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
@app.get("/list_files/")
def list_files(start_path: str = "."):
    """
    Lista todos los archivos y carpetas desde una ruta base.

    Args:
        start_path (str): Ruta base desde la cual listar (por defecto ".")

    Returns:
        dict: Estructura de archivos y carpetas.
    """
    file_structure = []

    for root, dirs, files in os.walk(start_path):
        for name in dirs:
            file_structure.append({
                "path": os.path.join(root, name),
                "type": "directory"
            })
        for name in files:
            file_structure.append({
                "path": os.path.join(root, name),
                "type": "file"
            })

    return JSONResponse(content={"files": file_structure})


#--- crea las carpetas
class CarpetaRequest(BaseModel):
    path: str

@app.post("/crear-carpeta")
def crear_carpeta(req: CarpetaRequest):
    try:
        os.makedirs(req.path, exist_ok=True)
        return {"path": req.path, "created": True, "message": "Carpeta creada o ya existía."}
    except Exception as e:
        return {"path": req.path, "created": False, "error": str(e)}
    

#---verificar estado del markdown
@app.get("/verificar_md/{filename}")
async def verificar_md(filename: str):
    md_path = os.path.join("output/clean", f"clean_{filename}.json")
    if os.path.exists(md_path):
        return JSONResponse(content={"disponible": True})
    return JSONResponse(status_code=202, content={"disponible": False})
