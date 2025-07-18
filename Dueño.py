
import asyncio
import flet as ft
from pydantic import ValidationError
from MongoDB import db
from datetime import datetime, date
from pymongo.collection import Collection
from bson import ObjectId
from schemas import MascotaBase, MascotaUpdate, FichaRapida, DuenioBase, DuenioUpdate
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from plantilla import crear_tabla_manual

from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException
from bson import ObjectId

class MascotaCRUD:

    mascotas = db["registro_mascotas"]
    duenios = db["registro_duenios"]

    @staticmethod
    def crear(mascota: MascotaBase, duenio_id: str):
        if not ObjectId.is_valid(duenio_id):
            raise HTTPException(status_code=400, detail="ID de dueño inválido")

        if not MascotaCRUD.duenios.find_one({"_id": ObjectId(duenio_id)}):
            raise HTTPException(status_code=404, detail="Dueño no encontrado")

        mascota_data = jsonable_encoder(mascota)
        mascota_data["duenio_id"] = ObjectId(duenio_id)
        insertado = MascotaCRUD.mascotas.insert_one(mascota_data)

        # Insertar también nombre y _id redundante
        MascotaCRUD.duenios.update_one(
            {"_id": ObjectId(duenio_id)},
            {"$push": {
                "mascotas": {
                    "_id": insertado.inserted_id,
                    "nombre": mascota.nombre
                }
            }}
        )

        return str(insertado.inserted_id)

    @staticmethod
    def actualizar(id: str, update: MascotaUpdate):
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="ID de mascota inválido")

        data = {k: v for k, v in update.model_dump(exclude_unset=True).items() if v is not None}
        if not data:
            raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")

        result = MascotaCRUD.mascotas.update_one({"_id": ObjectId(id)}, {"$set": data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Mascota no encontrada")

        # Si cambió el nombre, actualizamos el nombre redundante dentro del dueño
        if "nombre" in data:
            mascota = MascotaCRUD.mascotas.find_one({"_id": ObjectId(id)})
            if mascota and "duenio_id" in mascota:
                MascotaCRUD.duenios.update_one(
                    {"_id": mascota["duenio_id"], "mascotas._id": ObjectId(id)},
                    {"$set": {"mascotas.$.nombre": data["nombre"]}}
                )

        return True

    @staticmethod
    def agregar_ficha(mascota_id: str, ficha: FichaRapida):
        if not ObjectId.is_valid(mascota_id):
            raise HTTPException(status_code=400, detail="ID de mascota inválido")

        result = MascotaCRUD.mascotas.update_one(
            {"_id": ObjectId(mascota_id)},
            {"$push": {"fichas": jsonable_encoder(ficha)}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Mascota no encontrada")

        return True

    @staticmethod
    def eliminar(id: str):
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="ID inválido")

        mascota = MascotaCRUD.mascotas.find_one_and_delete({"_id": ObjectId(id)})
        if not mascota:
            raise HTTPException(status_code=404, detail="Mascota no encontrada")

        duenio_id = mascota.get("duenio_id")
        if duenio_id:
            MascotaCRUD.duenios.update_one(
                {"_id": duenio_id},
                {"$pull": {"mascotas": {"_id": ObjectId(id)}}}
            )

        return True
    

    @staticmethod
    def mostrarFichas(page, mascota_id: str):
        mascota = MascotaCRUD.mascotas.find_one({"_id": ObjectId(mascota_id)})
        if not mascota:
            return

        fichas = mascota.get("fichas", [])
        for ficha in fichas:
            ficha["fecha"] = str(ficha.get("fecha", ""))

        def cerrar(e=None):
            bs.open = False
            page.update()

        bs = ft.BottomSheet(
            ft.Container(
                ft.Column([
                    ft.Text("Fichas Médicas", size=20, weight=ft.FontWeight.BOLD),
                    crear_tabla_manual(fichas, lambda e, i: print("Ficha seleccionada"))
                ]),
                padding=20
            ),
            open=True,
            on_dismiss=cerrar
        )
        page.overlay.append(bs)
        page.update()
    
    @staticmethod
    def crearFichaView(page, mascota_id: str, veterinario_encargado: str):
        campos = {
            "diagnostico": ft.TextField(label="Diagnóstico", border_color=ft.Colors.PRIMARY),
            "tratamiento": ft.TextField(label="Tratamiento", border_color=ft.Colors.PRIMARY),
            "examen": ft.TextField(label="Examen", border_color=ft.Colors.PRIMARY),
        }

        error = ft.Text(value="", color=ft.Colors.ERROR)

        def cerrar_bs(e=None):
            bs.open = False
            error.value = ""
            for campo in campos.values():
                campo.value = ""
            page.update()

        def crear_ficha(e):
            error.value = ""
            try:
                ficha = FichaRapida(
                    fecha=date.today(),
                    diagnostico=campos["diagnostico"].value,
                    tratamiento=campos["tratamiento"].value,
                    examen=campos["examen"].value,
                    veterinario_encargado=veterinario_encargado
                )

                MascotaCRUD.mascotas.update_one(
                    {"_id": ObjectId(mascota_id)},
                    {"$push": {"fichas": jsonable_encoder(ficha)}}
                )
                cerrar_bs()

            except ValidationError as ve:
                # Extrae los errores uno por uno (puede haber varios, aquí se toma el primero)
                error.value = ve.errors()[0]["msg"]

            except Exception as ex:
                error.value = str(ex)
            page.update()

        bs = ft.BottomSheet(
            ft.Container(
                ft.Column([
                    ft.Text("Nueva Ficha Médica", size=20, weight=ft.FontWeight.BOLD),
                    ft.Column(list(campos.values()), height=200, scroll=ft.ScrollMode.AUTO),
                    error,
                    ft.Row([
                        ft.ElevatedButton("Cancelar", on_click=cerrar_bs),
                        ft.ElevatedButton("Crear", bgcolor=ft.Colors.PRIMARY, color=ft.Colors.WHITE, on_click=crear_ficha),
                    ], alignment=ft.MainAxisAlignment.END)
                ]),
                padding=20
            ),
            open=True,
            on_dismiss=cerrar_bs
        )

        page.overlay.append(bs)
        page.update()


    @staticmethod
    def mostrarDetallesView(page, mascota_id: str):
        mascota = MascotaCRUD.mascotas.find_one({"_id": ObjectId(mascota_id)})
        if not mascota:
            return

        campos = [
            ("Nombre", mascota.get("nombre", "")),
            ("Especie", mascota.get("especie", "")),
            ("Raza", mascota.get("raza", "")),
            ("Sexo", mascota.get("sexo", "")),
            ("Peso", str(mascota.get("peso", ""))),
            ("Fecha de Nacimiento", str(mascota.get("fecha_nacimiento", "")))
        ]

        def cerrar(e=None):
            bs.open = False
            page.update()

        bs = ft.BottomSheet(
            ft.Container(
                ft.Column([
                    ft.Text("Detalles de la Mascota", size=20, weight=ft.FontWeight.BOLD),
                    ft.Column([
                        ft.Row([
                            ft.Text(f"{label}: ", weight=ft.FontWeight.BOLD, size=18),
                            ft.Text(valor,  size=16)
                        ]) for label, valor in campos
                    ], scroll=ft.ScrollMode.AUTO, height=240),
                    ft.Row([
                        ft.ElevatedButton("Ver Fichas", icon=ft.Icons.MEDICAL_SERVICES, on_click=lambda e: MascotaCRUD.mostrarFichas(page, mascota_id))
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
    def mostrarView(duenio_id: str):
        if not ObjectId.is_valid(duenio_id):
            raise HTTPException(status_code=400, detail="ID de dueño inválido")

        duenio = MascotaCRUD.duenios.find_one({"_id": ObjectId(duenio_id)})
        if not duenio:
            raise HTTPException(status_code=404, detail="Dueño no encontrado")

        mascota_ids = duenio.get("mascotas", [])
        
        try:
            objetos_ids = [ObjectId(m["_id"] if isinstance(m, dict) else m) for m in mascota_ids]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al convertir ids de mascota: {e}")

        mascotas = list(MascotaCRUD.mascotas.find({"_id": {"$in": objetos_ids}}))

        lista = []
        for m in mascotas:
            m["_id"] = str(m["_id"])
            nombre = m.get("nombre", "Sin nombre")
            raza = m.get("raza", "Sin raza")
            fecha_nac = m.get("fecha_nacimiento")
            try:
                edad = datetime.now().year - datetime.strptime(fecha_nac, "%Y-%m-%d").year
            except:
                edad = "?"

            lista.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.PETS),
                    title=ft.Text(nombre),
                    subtitle=ft.Text(f"{raza} • {edad} años"),
                    on_click=lambda e, mid=m["_id"]: MascotaCRUD.mostrarDetallesView(e.control.page, mid)
                )
            )

        return ft.Column(lista if lista else [ft.Text("No hay mascotas")], scroll=ft.ScrollMode.AUTO, height=235)



    @staticmethod
    def crearView(page, duenio_id: str):
        campos = {
            "nombre": ft.TextField(label="Nombre", border_color=ft.Colors.INVERSE_PRIMARY),
            "especie": ft.TextField(label="Especie", border_color=ft.Colors.INVERSE_PRIMARY),
            "raza": ft.TextField(label="Raza", border_color=ft.Colors.INVERSE_PRIMARY),
            "sexo": ft.Dropdown(
                label="Sexo",
                options=[
                    ft.dropdown.Option("Macho"),
                    ft.dropdown.Option("Hembra")
                ],
                border_color=ft.Colors.INVERSE_PRIMARY
            ),
            "peso": ft.TextField(label="Peso (kg)", keyboard_type=ft.KeyboardType.NUMBER, border_color=ft.Colors.INVERSE_PRIMARY),
            "fecha_nacimiento": ft.TextField(label="Fecha de nacimiento (AAAA-MM-DD)", border_color=ft.Colors.INVERSE_PRIMARY),
        }

        error = ft.Text(value="", color=ft.Colors.ERROR, selectable=True)

        def cerrar_bs(e=None):
            bs.open = False
            error.value = ""
            for campo in campos.values():
                campo.value = ""
            page.update()

        def crear_mascota(e):
            error.value = ""
            try:
                data = {
                    "nombre": campos["nombre"].value,
                    "especie": campos["especie"].value,
                    "raza": campos["raza"].value,
                    "sexo": campos["sexo"].value,
                    "peso": float(campos["peso"].value),
                    "fecha_nacimiento": datetime.strptime(campos["fecha_nacimiento"].value, "%Y-%m-%d").date(),
                    "fichas": []
                }
                
                mascota = MascotaBase(**data)
                MascotaCRUD.crear(mascota, duenio_id)
                cerrar_bs()

            except ValidationError as ve:
                error.value = ve.errors()[0]["msg"]
            except Exception as ex:
                error.value = f"Error: {str(ex)}"
            page.update()

        bs = ft.BottomSheet(
            ft.Container(
                ft.Column([
                    ft.Text("Crear nueva mascota", size=20, weight=ft.FontWeight.BOLD),
                    ft.Column(campos.values(), height=250, scroll=ft.ScrollMode.AUTO),
                    error,
                    ft.Row([
                        ft.ElevatedButton("Cancelar", on_click=cerrar_bs),
                        ft.ElevatedButton(
                            "Crear",
                            bgcolor=ft.Colors.PRIMARY,
                            color=ft.Colors.ON_PRIMARY,
                            icon=ft.Icons.SAVE,
                            on_click=crear_mascota
                        ),
                    ], alignment=ft.MainAxisAlignment.END)
                ]),
                padding=20
            ),
            open=True,
            on_dismiss=cerrar_bs
        )

        page.overlay.append(bs)
        page.update()

    @staticmethod
    def obtener_nombres_por_duenio(cedula: str):
        duenio = DuenioCRUD.duenios.find_one({"cedula": cedula})
        if not duenio:
            return []
        ids = duenio.get("mascotas", [])
        mascotas = MascotaCRUD.mascotas.find({"_id": {"$in": [ObjectId(m["_id"] if isinstance(m, dict) else m) for m in ids]}})
        return [m.get("nombre", "Sin nombre") for m in mascotas]



class DuenioCRUD:
    # Variable de clase (compartida por todos los métodos)
    duenios = db["registro_duenios"]

    @staticmethod
    def crear(duenio: DuenioBase):
        data = jsonable_encoder(duenio)
        insertado = DuenioCRUD.duenios.insert_one(data)
        return str(insertado.inserted_id)

    @staticmethod
    def actualizar(id: str, update: DuenioUpdate):
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="ID inválido de dueño")

        data = {k: v for k, v in update.model_dump(exclude_unset=True).items() if v is not None}
        if not data:
            raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")

        result = DuenioCRUD.duenios.update_one({ "_id": ObjectId(id) }, { "$set": data })

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Dueño no encontrado")

        return True

    @staticmethod
    def eliminar(id: str):
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="ID inválido")

        resultado = DuenioCRUD.duenios.delete_one({ "_id": ObjectId(id) })
        if resultado.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Dueño no encontrado")

        return True

    @staticmethod
    def buscar(prompt: str = ""):
        if not prompt.strip():
            resultados = list(DuenioCRUD.duenios.find())
        else:
            primer_doc = DuenioCRUD.duenios.find_one()
            if not primer_doc:
                return []

            regex = {"$regex": prompt, "$options": "i"}
            condiciones = []
            for campo in primer_doc:
                if campo == "_id":
                    continue
                condiciones.append({ campo: regex })

            resultados = list(DuenioCRUD.duenios.find({ "$or": condiciones }))

        for doc in resultados:
            doc["_id"] = str(doc["_id"])
            if "mascotas" in doc:
                doc["mascotas"] = [str(m) for m in doc["mascotas"]]
    
        return resultados

    @staticmethod
    def mostrarDetalleView(page, duenio_id: str):
        duenio = DuenioCRUD.duenios.find_one({"_id": ObjectId(duenio_id)})
        if not duenio:
            return

        # Campos del dueño
        # campos = {
        #     "nombre": ft.TextField(label="Nombre", value=duenio.get("nombre", ""), disabled=True),
        #     "cedula": ft.TextField(label="Cédula", value=duenio.get("cedula", ""), disabled=True),
        #     "gmail": ft.TextField(label="Correo", value=duenio.get("gmail", ""), disabled=True),
        #     "telefono": ft.TextField(label="Teléfono", value=duenio.get("telefono", ""), disabled=True),
        #     "direccion": ft.TextField(label="Dirección", value=duenio.get("direccion", ""), disabled=True),
        # }

        # Vista de mascotas
        mascotas_view = MascotaCRUD.mostrarView(str(duenio["_id"]))

        def cerrar_bs(e=None):
            bs.open = False
            page.update()
        ft.Text()
        bs = ft.BottomSheet(
            ft.Container(
                ft.Column(
                    [
                        # Título con el nombre del dueño
                        ft.Text(
                            f"{duenio.get('nombre', 'Sin nombre')}",
                            size=20,
                            weight=ft.FontWeight.BOLD
                        ),

                        # # Formulario (solo lectura)
                        # ft.Column(
                        #     list(campos.values()),
                        #     scroll=ft.ScrollMode.AUTO,
                        #     height=200
                        # ),

                        # ft.Divider(),

                        # Título de mascotas
                        ft.Text("Mascotas", size=16, weight=ft.FontWeight.W_600),

                        # Lista de mascotas
                        mascotas_view,

                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    "Nueva",
                                    icon=ft.Icons.PETS,
                                    style=ft.ButtonStyle(
                                        bgcolor=ft.Colors.SECONDARY_CONTAINER,
                                    ),
                                    on_click=lambda e: MascotaCRUD.crearView(e.control.page, duenio_id)  # luego reemplazas
                                ),
                                ft.ElevatedButton(
                                    "Actualizar",
                                    icon=ft.Icons.EDIT,
                                    style=ft.ButtonStyle(
                                        bgcolor=ft.Colors.PRIMARY,
                                        color=ft.Colors.ON_PRIMARY
                                    ),
                                    on_click=lambda e: print("Actualizar dueño")
                                ),
                                ft.ElevatedButton(
                                    "Eliminar",
                                    icon=ft.Icons.DELETE,
                                    style=ft.ButtonStyle(
                                        bgcolor=ft.Colors.ERROR_CONTAINER,
                                        color=ft.Colors.ON_ERROR_CONTAINER
                                    ),
                                    on_click=lambda e: print("Eliminar dueño")
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.END
                        )
                    ]
                ),
                padding=20
            ),
            open=True,
            on_dismiss=cerrar_bs
        )

        page.overlay.append(bs)
        page.update()


    @staticmethod
    def mostrarView(busqueda: str = ""):
        datos = DuenioCRUD.buscar(busqueda)
        print(f"Datos:  {datos}")
        return crear_tabla_manual(
            datos,
            lambda e, i: DuenioCRUD.mostrarDetalleView(e.control.page, i),
            ["mascotas"]
        )
    
    @staticmethod
    def crearView(page):
        # Campos de entrada
        campos = {
            "nombre": ft.TextField(label="Nombre", border_color=ft.Colors.INVERSE_PRIMARY),
            "cedula": ft.TextField(label="Cédula", border_color=ft.Colors.INVERSE_PRIMARY),
            "gmail": ft.TextField(label="Correo electrónico", border_color=ft.Colors.INVERSE_PRIMARY, keyboard_type=ft.KeyboardType.EMAIL),
            "telefono": ft.TextField(label="Celular", border_color=ft.Colors.INVERSE_PRIMARY, keyboard_type=ft.KeyboardType.PHONE),
            "direccion": ft.TextField(label="Dirección", border_color=ft.Colors.INVERSE_PRIMARY),
        }

        error = ft.Text(value="", color=ft.Colors.RED)

        def cerrar_bs(e=None):
            bs.open = False
            error.value = ""
            for campo in campos.values():
                campo.value = ""
            page.update()

        def crear_dueño(e):
            error.value = ""
            try:
                data = {k: v.value for k, v in campos.items()}
                duenio = DuenioBase(**data)

                if DuenioCRUD.duenios.find_one({ "cedula": duenio.cedula }):
                    error.value = "Ya existe un dueño con esa cédula."
                else:
                    data = jsonable_encoder(duenio)
                    DuenioCRUD.duenios.insert_one(data)
                    cerrar_bs()

            except ValidationError as ve:
                error.value = ve.errors()[0]["msg"]
            
            page.update()
            #recargar(e)
            

        bs = ft.BottomSheet(
            ft.Container(
                ft.Column(
                    [
                        ft.Text("Crear nuevo dueño", size=20, weight=ft.FontWeight.BOLD, ),
                        ft.Column(campos.values(),scroll=ft.ScrollMode.AUTO, height=235),
                        error,
                        ft.Row(
                            [
                                ft.ElevatedButton("Cancelar", on_click=cerrar_bs),
                                ft.ElevatedButton(
                                    "Crear",
                                    bgcolor=ft.Colors.PRIMARY,
                                    color=ft.Colors.WHITE,
                                    on_click=crear_dueño
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.END
                        )
                    ],
                    
                ),
                padding=20,
                
            ),
            open=True,
            on_dismiss=cerrar_bs
        )

        page.overlay.append(bs)
        page.update()


    @staticmethod
    def obtener_cedulas():
        return [d.get("cedula", "Sin nombre") for d in DuenioCRUD.duenios.find()]


