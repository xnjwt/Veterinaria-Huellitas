from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import List, Optional
from bson import ObjectId
from datetime import time, timedelta, datetime,date
from bson import ObjectId
from pydantic_core import core_schema
from pydantic import GetCoreSchemaHandler

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        return core_schema.union_schema(
            [
                core_schema.is_instance_schema(ObjectId),
                core_schema.str_schema(),
            ],
            serialization=core_schema.plain_serializer_function_ser_schema(lambda x: str(x)),
        )

class FichaRapida(BaseModel):
    fecha: date
    diagnostico: str = Field(...,min_length=5, max_length=200)
    tratamiento: str = Field(...,min_length=5, max_length=300)
    examen: str = Field(...,min_length=5, max_length=200)


class MascotaBase(BaseModel):
    nombre: str = Field(...,min_length=3, max_length=100)
    especie: str = Field(...,min_length=3, max_length=50)
    raza: str = Field(...,min_length=3, max_length=50)
    sexo: str = Field(..., pattern=r"^(Macho|Hembra)$")
    peso: float = Field(..., ge=0)
    fecha_nacimiento: date
    fichas: List[FichaRapida] = []

    @field_validator("fecha_nacimiento")
    def validar_fecha_nacimiento(cls, v: date):
        if v > date.today():
            raise ValueError("La fecha de nacimiento debe ser menor o igual a hoy")
        return v

class MascotaUpdate(BaseModel):
    especie: Optional[str] = Field(None, max_length=50)
    raza: Optional[str] = Field(None, max_length=50)
    sexo: Optional[str] = Field(None, pattern=r"^(Macho|Hembra)$")
    peso: Optional[float] = Field(None, ge=0)
    fecha_nacimiento: Optional[date]
    fichas: Optional[List[FichaRapida]]


class DuenioBase(BaseModel):
    cedula: str = Field(..., pattern=r"^\d{10}$")
    nombre: str = Field(...,min_length=5, max_length=100)
    gmail: EmailStr
    telefono: str = Field(..., pattern=r"^09\d{8}$")
    direccion: str = Field(..., max_length=200)
    mascotas: List[PyObjectId] = []

class DuenioUpdate(BaseModel):
    gmail: Optional[EmailStr]
    telefono: Optional[str] = Field(None, pattern=r"^09\d{8}$")
    direccion: Optional[str] = Field(None, max_length=200)
    mascotas: Optional[List[PyObjectId]]

class CitaBase(BaseModel):
    fechaInicio: datetime
    duenio: PyObjectId
    mascota: PyObjectId
    veterinario: str = Field(..., max_length=100)
    duracion: int = Field(..., ge=1)  
    estado: str = Field("ausente", max_length=50)

    @field_validator('fechaInicio')
    def validar_fecha_no_fines_de_semana(cls, fechaInicio: datetime):
        if fechaInicio.weekday() in (5, 6): 
            raise ValueError("Las citas no pueden agendarse sábado o domingo")
        return fechaInicio

    @field_validator('fechaInicio')
    def validar_horario_laboral(cls, fechaInicio: datetime, info):
        duracion = info.data.get("duracion_minutos", 0)
        hora_inicio = fechaInicio.time()

        hora_min = time(8, 0)
        hora_max = time(16, 0)

        fin = (fechaInicio + timedelta(minutes=duracion)).time()

        if hora_inicio < hora_min:
            raise ValueError("La hora de inicio debe ser después de las 8:00 AM")

        if fin > hora_max:
            raise ValueError("La cita no puede extenderse más allá de las 4:00 PM")

        return fechaInicio
    @field_validator('duracion')
    def validar_duracion(cls, v):
        if v < 30:
            raise ValueError("La duración mínima debe ser de 30 minutos")
        return v

class CitaUpdate(BaseModel):
    fechaInicio: Optional[datetime]
    veterinario: Optional[str] = Field(None, max_length=100)
    estado: Optional[str] = Field(None, max_length=50)


class EmpleadoBase(BaseModel):
    rol: str = Field(..., max_length=50, min_length=5)
    nombre: str = Field(..., max_length=100,min_length=5)
    especialidad: str = Field(..., max_length=100)
    estado: str = Field(..., description="activo o fuera de servicio")

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v: str):
        estado_normalizado = v.lower().strip()
        if estado_normalizado not in {"activo", "fuera de servicio"}:
            raise ValueError("Estado debe ser 'activo' o 'fuera de servicio'")
        return estado_normalizado

class EmpleadoUpdate(BaseModel):
    rol: Optional[str] = Field(default=None, max_length=50)
    nombre: Optional[str] = Field(default=None, max_length=100)
    especialidad: Optional[str] = Field(default=None, max_length=100)
    estado: Optional[str] = Field(default="Ausente")

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v: Optional[str]):
        if v is None:
            return v
        estado_normalizado = v.lower().strip()
        if estado_normalizado not in {"activo", "fuera de servicio"}:
            raise ValueError("Estado debe ser 'activo' o 'fuera de servicio'")
        return estado_normalizado

class ServicioBase(BaseModel):
    nombre: str = Field(..., min_length=4,max_length=100)
    descripcion: str = Field(..., min_length=4, max_length=300)
    veterinario: str = Field(..., max_length=100)
    duenio: str = Field(..., max_length=100)
    pago: float = Field(..., ge=0)