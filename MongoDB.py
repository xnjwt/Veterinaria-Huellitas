from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os

load_dotenv()

CONTRA = os.getenv("MONGODB_CONTRA")
USUARIO = os.getenv("MONGODB_USUARIO")
if CONTRA is None:
    raise Exception("No se encontró la variable MONGODB_CONTRA en el archivo .env")

URI = f"mongodb+srv://{USUARIO}:{CONTRA}@veterinaria.c7hgxjn.mongodb.net/?retryWrites=true&w=majority&appName=Veterinaria"
cliente = MongoClient(URI, server_api=ServerApi('1')) #De no funcionar con la base de datos en la nube, ejecutar en la base local con lo siguiente: MongoClient("mongodb://localhost:27017", server_api=ServerApi('1'))
db = cliente["Veterinaria"]

try:
    cliente.admin.command('ping')
    print("Conectado exitosamente a MongoDB.")
except Exception as e:
    print("Error conectando a MongoDB:", e)
