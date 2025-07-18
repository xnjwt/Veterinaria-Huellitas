from pymongo import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://admin:admin@veterinaria.c7hgxjn.mongodb.net/?retryWrites=true&w=majority&appName=Veterinaria"
client = MongoClient(uri)

try:
    client.admin.command("ping")
    print("✅ Conectado exitosamente")
except Exception as e:
    print("❌ Error:", e)
