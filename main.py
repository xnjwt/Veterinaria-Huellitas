import asyncio
from datetime import time
import flet as ft
import threading
from Dueño import DuenioCRUD
from Citas import CitaCRUD
from Empleados import EmpleadoCRUD
from Servicios import ServicioCRUD


class Destino:

    def __init__(self, index, name, label, icon, selected_icon):

        self.index = index
        self.name = name
        self.label = label
        self.icon = icon
        self.selected_icon = selected_icon


destinos = [
    Destino(0, "dueños", "Dueños y Mascotas", ft.Icons.PEOPLE_OUTLINE, ft.Icons.PEOPLE),
    Destino(
        1,
        "empleados",
        "Empleados",
        ft.Icons.MEDICATION_OUTLINED,
        ft.Icons.MEDICATION,
    ),
    Destino(2, "citas", "Citas", ft.Icons.CALENDAR_TODAY, ft.Icons.EVENT),
    Destino(
        3,
        "servicios",
        "Servicios",
        ft.Icons.MEDICAL_SERVICES_OUTLINED,
        ft.Icons.MEDICAL_SERVICES,
    ),
]


class PopupColorItem(ft.PopupMenuItem):
    def __init__(self, color, name):
        super().__init__()
        self.content = ft.Row(
            controls=[
                ft.Icon(name=ft.Icons.COLOR_LENS_OUTLINED, color=color),
                ft.Text(name),
            ]
        )
        self.on_click = self.seed_color_changed
        self.data = color

    def seed_color_changed(self, e):
        self.page.theme = self.page.dark_theme = ft.Theme(color_scheme_seed=self.data)
        self.page.update()


class NavigationItem(ft.Container):
    def __init__(self, destination, item_clicked):
        super().__init__()
        self.ink = True
        self.padding = 10
        self.border_radius = 5
        self.destination = destination
        self.content = ft.Icon(destination.icon, tooltip=destination.label)
        self.on_click = item_clicked


class NavigationColumn(ft.Column):
    def __init__(self, gallery):
        super().__init__()
        self.expand = 4
        self.spacing = 0
        self.scroll = ft.ScrollMode.ALWAYS
        self.gallery = gallery
        self.selected_index = 0
        self.controls = self.get_navigation_items()

    def before_update(self):
        super().before_update()
        self.update_selected_item()

    def get_navigation_items(self):
        return [
            NavigationItem(dest, self.item_clicked) for dest in self.gallery.destinos
        ]

    def item_clicked(self, e):
        self.selected_index = e.control.destination.index
        self.update_selected_item()
        self.page.go(f"/{e.control.destination.name}")

    def update_selected_item(self):
        for item in self.controls:
            item.bgcolor = None
            item.content.name = item.destination.icon
        seleccionado = self.controls[self.selected_index]
        seleccionado.bgcolor = ft.Colors.SECONDARY_CONTAINER
        seleccionado.content.name = seleccionado.destination.selected_icon


class LeftNavigationMenu(ft.Column):
    def __init__(self, gallery):
        super().__init__()
        self.gallery = gallery
        self.rail = NavigationColumn(gallery=gallery)

        self.dark_light_text = ft.Text("Light theme")
        self.dark_light_icon = ft.IconButton(
            icon=ft.Icons.BRIGHTNESS_2_OUTLINED,
            tooltip="Cambiar tema claro/oscuro",
            on_click=self.theme_changed,
        )

        self.controls = [
            self.rail,
            ft.Column(
                expand=1,
                controls=[
                    self.dark_light_icon,
                    ft.PopupMenuButton(
                        icon=ft.Icons.COLOR_LENS_OUTLINED,
                        items=[
                            PopupColorItem("cyan", "Cyan"),
                            PopupColorItem("indigo", "Índigo"),
                            PopupColorItem("blue", "Azul"),
                            PopupColorItem("teal", "Verde marino"),
                            PopupColorItem("pink", "Rosado"),
                        ],
                    ),
                ],
            ),
        ]

    def theme_changed(self, e):
        if self.page.theme_mode == ft.ThemeMode.LIGHT:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.dark_light_icon.icon = ft.Icons.BRIGHTNESS_HIGH
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.dark_light_icon.icon = ft.Icons.BRIGHTNESS_2
        self.page.update()


debounce_timer = None


def main(page: ft.Page):
    page.window.icon = (
        r"C:\\Users\\user\\Desktop\\Proy\\veterinaria\\src\\assets\\icon.png"
    )
    page.theme = ft.Theme(color_scheme_seed="lightblue")
    page.title = "Veterinaria Huellitas"

    async def recargar_vista():
        await asyncio.sleep(1)
        nuevo_contenido = get_page_content(mostrar["actual"])
        nuevo_contenido.key = str(time())
        content_area.content.controls[1] = nuevo_contenido
        page.update()


    crear = {
        "dueños": lambda: DuenioCRUD.crearView(page),
        "empleados": lambda: EmpleadoCRUD.crearView(page),
        "citas": lambda: CitaCRUD.crearView(page),
    }
    mostrar = {
        "dueños": lambda b: DuenioCRUD.mostrarView(b),
        "citas": lambda b: CitaCRUD.mostrarView(b, page),
        "empleados": lambda b: EmpleadoCRUD.mostrarView(b),
        "servicios": lambda b: ServicioCRUD.mostrarView(b),
        "actual": "dueños",
        "busqueda": "",
    }

    def get_page_content(nombre):
        mostrar["actual"] = nombre
        print(f"Accediendo a la página: {nombre}")
        if nombre in mostrar.keys():
            print(f"Busqueda actual: {mostrar['busqueda']}")
            return mostrar[nombre](mostrar["busqueda"])
        else:
            return ft.Text(f"Página de {nombre}", size=25)

    def AbrirCrearPestaña(pagina):

        tieneCrear = crear.get(pagina, None)

        if tieneCrear is None:
            return
        crear[pagina]()

    page.floating_action_button = ft.FloatingActionButton(
        content=ft.Icon(ft.Icons.ADD, color=ft.Colors.ON_PRIMARY),
        bgcolor=ft.Colors.PRIMARY,
        tooltip="Agregar nuevo elemento",
        on_click=lambda e: AbrirCrearPestaña(mostrar["actual"]),
    )

    class Gallery:
        def __init__(self):
            self.destinos = destinos

    gallery = Gallery()
    navigation = LeftNavigationMenu(gallery=gallery)

    def actualizar_busqueda(e):
        global debounce_timer

        def hacer_busqueda():
            mostrar["busqueda"] = e.control.value
            contenido_actualizado = get_page_content(mostrar["actual"])
            content_area.content.controls[1] = contenido_actualizado
            page.update()

        if debounce_timer:
            debounce_timer.cancel()

        # Espera 0.3 segundos después de dejar de escribir
        debounce_timer = threading.Timer(0.5, hacer_busqueda)
        debounce_timer.start()

    busqueda_input = ft.TextField(
        value=mostrar["busqueda"],
        on_change=lambda e: actualizar_busqueda(e),
        border_radius=100,
        border_color=ft.Colors.INVERSE_PRIMARY,
        prefix_icon=ft.Icons.SEARCH,
    )

    tf = ft.Row([busqueda_input], alignment=ft.MainAxisAlignment.END, width=1000)

    content_area = ft.Container(
        content=ft.Column(
            [tf, get_page_content("dueños")],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        expand=True,
        padding=10,
    )

    def route_change(e):
        ruta = page.route.strip("/")
        destino = next((d for d in destinos if d.name == ruta), None)
        if destino:
            mostrar["actual"] = destino.name
            content_area.content.controls[1] = get_page_content(destino.name)

            page.update()

    page.on_route_change = route_change

    page.add(
        ft.Row(
            controls=[
                navigation,
                ft.VerticalDivider(width=1, color=ft.Colors.OUTLINE_VARIANT),
                content_area,
            ],
            expand=True,
        )
    )
    
    page.go("/dueños")


ft.app(target=main, view=ft.AppView.WEB_BROWSER)
