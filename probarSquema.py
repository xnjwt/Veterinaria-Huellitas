from schemas import CitaBase
from bson import ObjectId
from datetime import datetime

cita = CitaBase(
    fechaInicio=datetime.now(),
    cliente=ObjectId("66a6fdf02fc42b394df0c230"),
    mascota=ObjectId("66a6fdf02fc42b394df0c231"),
    veterinario="Juan Pérez",
    duracion=30,
    estado="pendiente"
)
print(cita)
