import asyncio
import flet as ft
from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException
from bson import ObjectId
from pydantic import ValidationError
from MongoDB import db
from schemas import CitaBase, CitaUpdate
from Empleados import EmpleadoCRUD
from Servicios import ServicioCRUD
from Dueño import DuenioCRUD, MascotaCRUD
from datetime import datetime, timedelta
from plantilla import dropdown_con_agregar
import locale

try:
    locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "es_ES")
    except locale.Error:
        # Usa configuración por defecto si no está disponible
        print("⚠️ Locale 'es_ES' no está disponible en este sistema. Usando configuración por defecto.")


class CitaCRUD:
    citas = db["registro_citas"]  # Asegúrate que 'db' ya esté definido correctamente

    @staticmethod
    def crear(cita: CitaBase):
        data = cita.model_dump()
        data["duracion"] = int(data["duracion"])
        insertado = CitaCRUD.citas.insert_one(data)
        return str(insertado.inserted_id)

    @staticmethod
    def actualizar(id: str, update: CitaUpdate):
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="ID inválido de cita")

        data = {
            k: v
            for k, v in update.model_dump(exclude_unset=True).items()
            if v is not None
        }

        if not data:
            raise HTTPException(
                status_code=400, detail="No se proporcionaron campos para actualizar"
            )

        resultado = CitaCRUD.citas.update_one({"_id": ObjectId(id)}, {"$set": data})

        if resultado.matched_count == 0:
            raise HTTPException(status_code=404, detail="Cita no encontrada")

        return True

    @staticmethod
    def eliminar(id: str):
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="ID inválido")

        resultado = CitaCRUD.citas.delete_one({"_id": ObjectId(id)})

        if resultado.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Cita no encontrada")

        return True

    @staticmethod
    def buscar(prompt: str = ""):
        if not prompt.strip():
            resultados = list(CitaCRUD.citas.find())
        else:
            primer_doc = CitaCRUD.citas.find_one()
            if not primer_doc:
                return []

            regex = {"$regex": prompt, "$options": "i"}
            condiciones = []
            for campo in primer_doc:
                if campo == "_id":
                    continue
                condiciones.append({campo: regex})

            resultados = list(CitaCRUD.citas.find({"$or": condiciones}))

        # Procesar resultados
        for doc in resultados:
            doc["_id"] = str(doc["_id"])
            doc["duenio"] = str(doc.get("duenio", ""))
            doc["mascota"] = str(doc.get("mascota", ""))
        return resultados

    @staticmethod
    def MostrarDetalladoView(id_cita, page):

        cita = CitaCRUD.citas.find_one({"_id": ObjectId(id_cita)})
        if not cita:
            page.dialog = ft.AlertDialog(title=ft.Text("Cita no encontrada"))
            page.open(page.dialog)
            return

        original_fecha = cita["fechaInicio"]
        if isinstance(original_fecha, str):
            original_fecha = datetime.fromisoformat(original_fecha)
        fecha_text = ft.Text(value=original_fecha.strftime("%Y-%m-%d"), weight="bold")
        hora_text = ft.Text(value=original_fecha.strftime("%H:%M"), weight="bold")

        fecha_picker = ft.DatePicker()
        time_picker = ft.TimePicker()

        def seleccionar_fecha(e):
            def actualizar_fecha(ev):
                fecha_text.value = ev.control.value.strftime("%Y-%m-%d")
                verificar_cambios()
                page.update()

            fecha_picker.on_change = actualizar_fecha
            page.dialog = fecha_picker
            page.open(fecha_picker)

        def seleccionar_hora(e):
            def actualizar_hora(ev):
                hora_text.value = time_picker.value.strftime("%H:%M")
                verificar_cambios()
                page.update()

            time_picker.on_change = actualizar_hora
            page.dialog = time_picker
            page.open(time_picker)

        def verificar_cambios():
            nueva_fecha = datetime.strptime(
                f"{fecha_text.value} {hora_text.value}", "%Y-%m-%d %H:%M"
            )
            reprogramar.visible = nueva_fecha != original_fecha
            page.update()

        # Campos read-only
        duenio = ft.TextField(label="Dueño", value=cita["duenio"], read_only=True)
        mascota = ft.TextField(label="Mascota", value=cita["mascota"], read_only=True)
        veterinario = ft.TextField(
            label="Veterinario", value=cita["veterinario"], read_only=True
        )
        duracion = ft.TextField(
            label="Duración", value=str(cita["duracion"]), read_only=True, expand=True
        )
        estado = ft.TextField(
            label="Estado", value=cita.get("estado", ""), read_only=True
        )

        error = ft.Text(color=ft.Colors.RED)

        def cerrar(e=None):
            contenedor.open = False
            page.update()

        def actualizar_fecha(e):
            try:
                nueva_fecha = datetime.strptime(
                    f"{fecha_text.value} {hora_text.value}", "%Y-%m-%d %H:%M"
                )
                CitaCRUD.citas.update_one(
                    {"_id": ObjectId(id_cita)}, {"$set": {"fechaInicio": nueva_fecha}}
                )
                error.value = "Fecha reprogramada"
                page.update()
            except ValidationError as ve:
                # Extrae los errores uno por uno (puede haber varios, aquí se toma el primero)
                error.value = ve.errors()[0]["msg"]
            except Exception as ex:
                error.value = str(ex)
                page.update()

        def marcar_asistencia(e):
            try:
                CitaCRUD.citas.update_one(
                    {"_id": ObjectId(id_cita)}, {"$set": {"estado": "asistió"}}
                )
                estado.value = "asistió"
                page.update()
            except ValidationError as ve:
                error.value = ve.errors()[0]["msg"]
            except Exception as ex:
                error.value = str(ex)
                page.update()

        # Hora actual vs fin de la cita
        ahora = datetime.now()
        fecha_fin = original_fecha + timedelta(minutes=cita["duracion"])

        reprogramar = ft.ElevatedButton(
            "Reprogramar", on_click=actualizar_fecha, visible=False
        )
        marcar = ft.ElevatedButton(
            "Asistió",
            on_click=marcar_asistencia,
            visible=fecha_fin > ahora and cita.get("estado") != "asistió",
        )
        atender = ft.ElevatedButton(
            "Atender",
            visible=fecha_fin > ahora,
            on_click=lambda e: MascotaCRUD.crearFichaView(
                page, cita.get("mascota"), cita.get("veterinario")
            ),
        )
        registrar = ft.ElevatedButton(
            "Reg. Servicio",
            visible=fecha_fin > ahora,
            on_click=lambda e: ServicioCRUD.crearView(
                page, cita.get("mascota"), cita.get("veterinario")
            ),
        )
        cancelar = ft.ElevatedButton("Cancelar", on_click=cerrar)

        botones = ft.Row(
            controls=[reprogramar, cancelar, marcar, atender, registrar],
            alignment=ft.MainAxisAlignment.END,
            wrap=True,
            expand=True,
        )

        contenedor = ft.BottomSheet(
            ft.Container(
                ft.Column(
                    [
                        ft.Text("Editar Cita", size=20, weight=ft.FontWeight.BOLD),
                        ft.Column(
                            [
                                duenio,
                                mascota,
                                veterinario,
                                ft.Row(
                                    [
                                        ft.Row(
                                            [
                                                ft.Container(
                                                    fecha_text,
                                                    border_radius=10,
                                                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                                    padding=10,
                                                    on_click=seleccionar_fecha,
                                                ),
                                                ft.Container(
                                                    hora_text,
                                                    border_radius=10,
                                                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                                    padding=10,
                                                    on_click=seleccionar_hora,
                                                ),
                                            ],
                                            expand=True,
                                        ),
                                        duracion,
                                    ],
                                    spacing=10,
                                ),
                                estado,
                                error,
                            ],
                            scroll=ft.ScrollMode.AUTO,
                            height=250,
                            spacing=10,
                        ),
                        botones,
                    ]
                ),
                padding=20,
                width=450,
            ),
            open=True,
            on_dismiss=cerrar,
        )

        page.overlay.append(contenedor)
        page.update()

    def mostrarView(busqueda, page=None):
        """Muestra una agenda semanal con filtro por veterinario

        Args:
            veterinarios: Lista de nombres de veterinarios
            eventos: Lista de diccionarios con eventos
            page: Objeto page de flet (opcional)
        """

        eventos = CitaCRUD.buscar(busqueda)
        veterinarios_activos = EmpleadoCRUD.obtener_veterinarios_activos()
        veterinarios = (
            veterinarios_activos if veterinarios_activos else ["Sin veterinarios"]
        )

        veterinario_seleccionado = veterinarios[0]
        hora_inicio = 8
        hora_fin = 16
        base_date = datetime.now()
        altura_encabezado = 60

        # Contenedor principal que será retornado
        contenedor_principal = ft.Column(expand=True)
        contenedor_tabla = ft.Column(spacing=0, expand=True)

        def obtener_semana(base):
            lunes = base - timedelta(days=base.weekday())
            return [lunes + timedelta(days=i) for i in range(5)]

        def dibujar_tabla():
            contenedor_tabla.controls.clear()
            semana = obtener_semana(base_date)

            # Filtrar eventos por veterinario seleccionado
            eventos_filtrados = [
                ev for ev in eventos if ev["veterinario"] == veterinario_seleccionado
            ]

            # Encabezado
            fila_encabezado = ft.Row(
                [
                    ft.Container(
                        ft.Text("Hora", weight="bold", offset=ft.Offset(0.2, -0.9)),
                        width=60,
                    )
                ]
                + [
                    ft.Container(
                        ft.Column(
                            [
                                ft.Text(d.strftime("%A").capitalize(), weight="bold"),
                                ft.Text(
                                    d.strftime("%d"),
                                    size=18,
                                    color=ft.Colors.OUTLINE_VARIANT,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=2,
                        ),
                        width=200,
                        alignment=ft.alignment.center,
                        padding=5,
                    )
                    for d in semana
                ],
                spacing=0,
            )
            contenedor_tabla.controls.append(fila_encabezado)

            # Precalcular posiciones de eventos
            eventos_globales = []
            for ev in eventos_filtrados:
                for dia in semana:
                    fechaInicio = ev["fechaInicio"]
                    if isinstance(fechaInicio, str):
                        fechaInicio = datetime.fromisoformat(fechaInicio)

                    if fechaInicio.date() == dia.date():
                        duracion = ev["duracion"]

                        dia_idx = semana.index(dia)
                        left = 60 + (dia_idx * 200)
                        top = (
                            altura_encabezado
                            + ((fechaInicio.hour - hora_inicio) * 60)
                            + fechaInicio.minute
                        )
                        height = duracion

                        eventos_globales.append(
                            {"top": top, "left": left, "height": height, "evento": ev}
                        )

            stack_global = ft.Stack(expand=True)

            # Dibujar fondo de la tabla
            for h in range(hora_inicio, hora_fin):
                fila = ft.Row(
                    [
                        ft.Container(
                            ft.Text(f"{h}:00"),
                            width=60,
                            height=60,
                            alignment=ft.alignment.top_center,
                            offset=ft.Offset(0, -0.2),
                        )
                    ],
                    spacing=0,
                )

                for dia in semana:
                    fondo = ft.Container(
                        width=200,
                        height=60,
                        border=ft.border.all(1, ft.Colors.SURFACE),
                        bgcolor=ft.Colors.ON_PRIMARY,
                    )
                    celda = ft.Container(
                        content=fondo, width=200, height=60, padding=0, margin=0
                    )
                    fila.controls.append(celda)

                contenedor_tabla.controls.append(fila)

            # Añadir eventos al stack global
            for ev_data in eventos_globales:
                ev = ev_data["evento"]
                evento = ft.Container(
                    on_click=lambda e, _id=ev["_id"]: CitaCRUD.MostrarDetalladoView(_id, page),
                    top=ev_data["top"],
                    left=ev_data["left"],
                    content=ft.Text(f'{ev["duenio"]} - {ev["mascota"]}', size=12),
                    bgcolor=ft.Colors.INVERSE_PRIMARY,
                    height=ev_data["height"] - 5,
                    width=190,
                    border_radius=ft.border_radius.all(6),
                    padding=ft.padding.all(5),
                    alignment=ft.alignment.top_left,
                )
                stack_global.controls.append(evento)

            # Crear dropdown de veterinarios
            dropdown_veterinarios = ft.Dropdown(
                label="Veterinario",
                hint_text="Seleccione un veterinario",
                options=[ft.dropdown.Option(vet) for vet in veterinarios],
                value=veterinario_seleccionado,
                width=200,
                on_change=lambda e: cambiar_veterinario(e.control.value),
            )

            # Fila superior con controles
            fila_superior = ft.Row(
                controls=[
                    dropdown_veterinarios,
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "<", on_click=lambda e: cambiar_semana(-7)
                            ),
                            ft.ElevatedButton(
                                ">", on_click=lambda e: cambiar_semana(7)
                            ),
                        ],
                        spacing=20,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                height=60,
                width=100 * 11 - 40,
            )

            # Actualizar contenedor principal
            contenedor_principal.controls.clear()
            contenedor_principal.controls.extend(
                [
                    fila_superior,
                    ft.Stack(controls=[contenedor_tabla, stack_global], expand=True),
                ]
            )

            if page:
                page.update()

        def cambiar_semana(delta):
            nonlocal base_date
            base_date += timedelta(days=delta)
            dibujar_tabla()

        def cambiar_veterinario(vet):
            nonlocal veterinario_seleccionado
            veterinario_seleccionado = vet
            dibujar_tabla()

        # Dibujar tabla inicial
        dibujar_tabla()

        return contenedor_principal

    @staticmethod
    def crearView(page):

        duenios = DuenioCRUD.obtener_cedulas()
        veterinarios = EmpleadoCRUD.obtener_veterinarios_activos()

        selected_duenio = ft.Ref[ft.Dropdown]()
        selected_mascota = ft.Ref[ft.Dropdown]()
        selected_veterinario = ft.Ref[ft.Dropdown]()

        fecha_actual = datetime.now()
        fecha_picker = ft.DatePicker(
            first_date=fecha_actual, last_date=datetime(fecha_actual.year + 1, 12, 31)
        )
        time_picker = ft.TimePicker()

        fecha_text = ft.Text(
            value=fecha_actual.strftime("%Y-%m-%d"),
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        )
        hora_text = ft.Text(
            value=fecha_actual.strftime("%H:%M"),
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        )

        def seleccionar_fecha(e):
            def actualizar_fecha(ev):
                fecha_text.value = ev.control.value.strftime("%Y-%m-%d")
                page.update()

            fecha_picker.on_change = actualizar_fecha
            page.dialog = fecha_picker
            page.open(fecha_picker)

        def seleccionar_hora(e):
            def actualizar_hora(ev):
                hora_text.value = time_picker.value.strftime("%H:%M")
                page.update()

            time_picker.on_change = actualizar_hora
            page.dialog = time_picker
            page.open(time_picker)

        dropdown_duenios = ft.Dropdown(
            label="Dueño",
            options=[ft.dropdown.Option(d) for d in duenios],
            ref=selected_duenio,
            expand=True,
        )
        dropdown_mascotas = ft.Dropdown(
            label="Mascota", options=[], ref=selected_mascota, expand=True
        )
        dropdown_veterinarios = ft.Dropdown(
            label="Veterinario",
            options=[ft.dropdown.Option(v) for v in veterinarios],
            ref=selected_veterinario,
            expand=True,
        )

        def actualizar_mascotas(e):
            cedula = selected_duenio.current.value
            nombres = MascotaCRUD.obtener_nombres_por_duenio(cedula)
            dropdown_mascotas.options = [ft.dropdown.Option(n) for n in nombres]
            page.update()

        selected_duenio.current = dropdown_duenios
        selected_duenio.current.on_change = actualizar_mascotas

        duracion = ft.TextField(
            label="Duración",
            suffix_text="min",
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=1,
        )

        error = ft.Text(color=ft.Colors.RED)

        def cerrar(e=None):
            contenedor.open = False
            error.value = ""
            page.update()

        def crear_cita(e):
            try:
                f = f"{fecha_text.value} {hora_text.value}"
                cita = CitaBase(
                    duenio=selected_duenio.current.value,
                    mascota=selected_mascota.current.value,
                    veterinario=selected_veterinario.current.value,
                    fechaInicio=datetime.strptime(f, "%Y-%m-%d %H:%M"),
                    duracion=int(duracion.value),
                )

                # Validación de colisiones
                inicio = cita.fechaInicio
                fin = inicio + timedelta(minutes=cita.duracion)
                conflictos = CitaCRUD.citas.find(
                    {
                        "veterinario": cita.veterinario,
                        "$expr": {
                            "$and": [
                                {"$lt": ["$fechaInicio", fin]},
                                {
                                    "$gt": [
                                        {
                                            "$dateAdd": {
                                                "startDate": "$fechaInicio",
                                                "unit": "minute",
                                                "amount": {"$toInt": "$duracion"},
                                            }
                                        },
                                        inicio,
                                    ]
                                },
                            ]
                        },
                    }
                )

                if list(conflictos):
                    error.value = "Este veterinario ya tiene una cita en ese horario."
                    page.update()
                    return

                CitaCRUD.crear(cita)
                cerrar()
            except ValidationError as ve:
                # Extrae los errores uno por uno (puede haber varios, aquí se toma el primero)
                error.value = ve.errors()[0]["msg"]
                page.update()            
            except Exception as ex:
                error.value = str(ex)
                page.update()

        contenedor = ft.BottomSheet(
            ft.Container(
                ft.Column(
                    [
                        ft.Text("Crear Cita", size=20, weight=ft.FontWeight.BOLD),
                        dropdown_duenios,
                        dropdown_mascotas,
                        dropdown_veterinarios,
                        ft.Row(
                            [
                                ft.Container(
                                    fecha_text,
                                    border_radius=10,
                                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                    padding=10,
                                    on_click=seleccionar_fecha,
                                    expand=True,
                                ),
                                ft.Container(
                                    hora_text,
                                    border_radius=10,
                                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                    padding=10,
                                    on_click=seleccionar_hora,
                                    expand=True,
                                ),
                                duracion,
                            ],
                            spacing=10,
                        ),
                        error,
                        ft.Row(
                            [
                                ft.ElevatedButton("Cancelar", on_click=cerrar),
                                ft.ElevatedButton(
                                    "Crear",
                                    on_click=crear_cita,
                                    bgcolor=ft.Colors.PRIMARY,
                                    color=ft.Colors.ON_PRIMARY,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.END,
                        ),
                    ]
                ),
                padding=20,
                width=400,
            ),
            open=True,
            on_dismiss=cerrar,
        )

        page.overlay.append(contenedor)
        page.update()
        #asyncio.create_task(recargar())
