import asyncio
import flet as ft
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from bson import ObjectId
from MongoDB import db
from schemas import EmpleadoBase, EmpleadoUpdate
from pydantic import ValidationError
from plantilla import crear_tabla_manual

class EmpleadoCRUD:
    empleados = db["registro_empleados"]

    @staticmethod
    def crear(empleado: EmpleadoBase):
        data = empleado.model_dump()
        insertado = EmpleadoCRUD.empleados.insert_one(data)
        return str(insertado.inserted_id)

    @staticmethod
    def actualizar(id: str, update: EmpleadoUpdate):
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="ID inválido")

        data = {k: v for k, v in update.model_dump(exclude_unset=True).items() if v is not None}
        if not data:
            raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")

        result = EmpleadoCRUD.empleados.update_one({"_id": ObjectId(id)}, {"$set": data})

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")

        return True

    @staticmethod
    def eliminar(id: str):
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="ID inválido")

        resultado = EmpleadoCRUD.empleados.delete_one({"_id": ObjectId(id)})
        if resultado.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")

        return True

    @staticmethod
    def buscar(prompt: str = ""):
        if not prompt.strip():
            resultados = list(EmpleadoCRUD.empleados.find())
        else:
            primer_doc = EmpleadoCRUD.empleados.find_one()
            if not primer_doc:
                return []

            regex = {"$regex": prompt, "$options": "i"}
            condiciones = []
            for campo in primer_doc:
                if campo == "_id":
                    continue
                condiciones.append({campo: regex})

            resultados = list(EmpleadoCRUD.empleados.find({"$or": condiciones}))

        for doc in resultados:
            doc["_id"] = str(doc["_id"])
        return resultados

    @staticmethod
    def mostrarView(busqueda: str = ""):
        datos = EmpleadoCRUD.buscar(busqueda)
        return crear_tabla_manual(
            datos,
            lambda e, i: EmpleadoCRUD.mostrarDetalleView(e.control.page, i)
        )

    @staticmethod
    def mostrarDetalleView(page, empleado_id: str):
        empleado = EmpleadoCRUD.empleados.find_one({"_id": ObjectId(empleado_id)})
        if not empleado:
            return

        campos = [
            ("Rol", empleado.get("rol", "")),
            ("Nombre", empleado.get("nombre", "")),
            ("Especialidad", empleado.get("especialidad", "")),
            ("Estado", empleado.get("estado", ""))
        ]

        def cerrar(e=None):
            bs.open = False
            page.update()

        bs = ft.BottomSheet(
            ft.Container(
                ft.Column([
                    ft.Text(f"Empleado: {empleado.get('nombre', 'Sin nombre')}", size=20, weight=ft.FontWeight.BOLD),
                    ft.Column([
                        ft.Row([
                            ft.Text(f"{label}: ", weight=ft.FontWeight.BOLD),
                            ft.Text(valor)
                        ]) for label, valor in campos
                    ], scroll=ft.ScrollMode.AUTO, height=200),
                    ft.Row([
                        ft.ElevatedButton("Actualizar", icon=ft.Icons.EDIT),
                        ft.ElevatedButton("Eliminar", icon=ft.Icons.DELETE, icon_color=ft.Colors.ERROR),
                    ], alignment=ft.MainAxisAlignment.END)
                ]),
                padding=20
            ),
            open=True,
            on_dismiss=cerrar
        )

        page.overlay.append(bs)
        page.update()

    @staticmethod
    def crearView(page):
        campos = {
            "rol": ft.Dropdown(
                label="Rol",
                options=[
                    ft.dropdown.Option("Veterinario"),
                    ft.dropdown.Option("Administrador"),
                    ft.dropdown.Option("Asistente")
                ],
                border_color=ft.Colors.INVERSE_PRIMARY
            ),
            "nombre": ft.TextField(label="Nombre", border_color=ft.Colors.INVERSE_PRIMARY),
            "especialidad": ft.TextField(label="Especialidad", border_color=ft.Colors.INVERSE_PRIMARY),
            "estado": ft.Dropdown(
                label="Estado",
                options=[
                    ft.dropdown.Option("activo"),
                    ft.dropdown.Option("fuera de servicio")
                ],
                border_color=ft.Colors.INVERSE_PRIMARY
            ),
        }

        error = ft.Text(value="", color=ft.Colors.RED)

        def cerrar_bs(e=None):
            bs.open = False
            error.value = ""
            for campo in campos.values():
                if isinstance(campo, ft.Dropdown):
                    campo.value = None
                else:
                    campo.value = ""
            page.update()

        def crear_empleado(e):
            error.value = ""
            try:
                data = {k: v.value for k, v in campos.items()}
                empleado = EmpleadoBase(**data)
                EmpleadoCRUD.crear(empleado)
                cerrar_bs()
            except ValidationError as ve:
                error.value = ve.errors()[0]["msg"]
            page.update()

        bs = ft.BottomSheet(
            ft.Container(
                ft.Column([
                    ft.Text("Crear nuevo empleado", size=20, weight=ft.FontWeight.BOLD),
                    ft.Column(list(campos.values()), scroll=ft.ScrollMode.AUTO, height=200),
                    error,
                    ft.Row([
                        ft.ElevatedButton("Cancelar", on_click=cerrar_bs),
                        ft.ElevatedButton("Crear", on_click=crear_empleado, bgcolor=ft.Colors.PRIMARY, color=ft.Colors.WHITE),
                    ], alignment=ft.MainAxisAlignment.END)
                ]),
                padding=20
            ),
            open=True,
            on_dismiss=cerrar_bs
        )

        page.overlay.append(bs)
        page.update()
        #asyncio.create_task(recargar())

    @staticmethod
    def obtener_veterinarios_activos():
        empleados = EmpleadoCRUD.empleados.find({
            "rol": {"$regex": "veterinario", "$options": "i"},
            "estado": "activo"
        })

        return [empleado["nombre"] for empleado in empleados]

