from pydantic import ValidationError

from fastapi.encoders import jsonable_encoder
from schemas import ServicioBase
from MongoDB import db
import flet as ft
from plantilla import crear_tabla_manual


class ServicioCRUD:
    servicios = db["registro_servicios"]

    @staticmethod
    def crear(servicio: ServicioBase):
        data = jsonable_encoder(servicio)
        resultado = ServicioCRUD.servicios.insert_one(data)
        return str(resultado.inserted_id)

    @staticmethod
    def buscar(prompt: str = ""):
        if not prompt.strip():
            resultados = list(ServicioCRUD.servicios.find())
        else:
            primer_doc = ServicioCRUD.servicios.find_one()
            if not primer_doc:
                return []

            regex = {"$regex": prompt, "$options": "i"}
            condiciones = []
            for campo in primer_doc:
                if campo == "_id":
                    continue
                condiciones.append({campo: regex})

            resultados = list(ServicioCRUD.servicios.find({"$or": condiciones}))

        for doc in resultados:
            doc["_id"] = str(doc["_id"])
        return resultados

    @staticmethod
    def mostrarView(busqueda: str = ""):
        datos = ServicioCRUD.buscar(busqueda)
        return crear_tabla_manual(
            datos,
            lambda e, i: print(
                f"Servicio {i} seleccionado"
            ),  # si quieres, puedes cambiar esto luego
            [],
        )

    @staticmethod
    def crearView(page, duenio: str, veterinario: str):
        # Campos no editables
        campos_fijos = {
            "veterinario": ft.TextField(
                label="Veterinario", value=veterinario, disabled=True
            ),
            "duenio": ft.TextField(label="Dueño", value=duenio, disabled=True),
        }

        # Campos editables
        campos = {
            "nombre": ft.TextField(
                label="Nombre del Servicio", border_color=ft.Colors.PRIMARY
            ),
            "descripcion": ft.TextField(
                label="Descripción", border_color=ft.Colors.PRIMARY
            ),
            "pago": ft.TextField(label="Pago ($)", border_color=ft.Colors.PRIMARY),
        }

        error = ft.Text(value="", color=ft.Colors.ERROR)

        def cerrar_bs(e=None):
            bs.open = False
            error.value = ""
            for campo in campos.values():
                campo.value = ""
            page.update()

        def crear_servicio(e):
            error.value = ""
            try:
                data = {
                    "veterinario": campos_fijos["veterinario"].value,
                    "duenio": campos_fijos["duenio"].value,
                    "nombre": campos["nombre"].value,
                    "descripcion": campos["descripcion"].value,
                    "pago": float(campos["pago"].value),
                }
                servicio = ServicioBase(**data)
                ServicioCRUD.crear(servicio)
                cerrar_bs()

            except ValidationError as ve:
                error.value = ve.errors()[0]["msg"]
            except ValueError:
                error.value = "El campo 'pago' debe ser un número."
            page.update()

        bs = ft.BottomSheet(
            ft.Container(
                ft.Column(
                    [
                        ft.Text("Crear Servicio", size=20, weight=ft.FontWeight.BOLD),
                        ft.Column(
                            [
                                ft.Column(campos_fijos.values()),
                                ft.Divider(),
                                ft.Column(
                                    campos.values(),
                                    
                                ),
                                error,
                            ],
                            scroll=ft.ScrollMode.AUTO,
                            height=250
                        ),
                        
                        ft.Row(
                            [
                                ft.ElevatedButton("Cancelar", on_click=cerrar_bs),
                                ft.ElevatedButton(
                                    "Crear",
                                    bgcolor=ft.Colors.PRIMARY,
                                    color=ft.Colors.WHITE,
                                    on_click=crear_servicio,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.END,
                        ),
                    ]
                ),
                padding=20,
            ),
            open=True,
            on_dismiss=cerrar_bs,
        )

        page.overlay.append(bs)
        page.update()
