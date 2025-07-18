import flet as ft
from flet import Colors

def crear_tabla_manual(datos: list[object], on_click, excluir_campos=[]):
    color_linea = Colors.PRIMARY_CONTAINER
    color_cabecera = Colors.INVERSE_PRIMARY
    color_cabecera_texto = Colors.PRIMARY
    lista_ids = [d['_id'] for d in datos[::-1]]

    excluir = ["_id"]
    excluir.extend(excluir_campos)

    for dict in datos:
        for campo in excluir:
            if campo in dict:
                del dict[campo]


    if not datos:
        return ft.Text("No hay datos para mostrar.", text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD, size=16)


    campos = list(datos[0].keys())
    header = ft.Container(
        content=ft.Row(
            [ft.Text(c.replace("_", " ").capitalize(), color=color_cabecera_texto, expand=1, weight=ft.FontWeight.BOLD, size=16, text_align=ft.TextAlign.CENTER) for c in campos],
            spacing=0,
            width=1000, 
        ),
        width=1000,
        height=60,
        bgcolor=color_cabecera,
        border_radius=8,
        padding=ft.padding.symmetric(0,30),
    )

    filas = []
    for idx, fila in enumerate(datos[::-1]):
        valores = list(fila.values())
        fila_cont = ft.Container(
            content=ft.Row(
                [ft.Text(str(v), expand=1, text_align=ft.TextAlign.CENTER) for v in valores],
                spacing=0
            ),
            width=1000,
            height=60,
            padding=ft.padding.symmetric(0, 30),
            # Sin bgcolor fijo
            border=ft.border.Border(
                bottom=ft.border.BorderSide(1, color_linea)
            ),
            # Efecto clic: fondo redondeado momentáneo
            ink=True,
            border_radius=8,
            on_click=lambda e, i=idx: on_click(e, lista_ids[i])
        )
        filas.append(fila_cont)

    return ft.Column([header, *filas], spacing=2, scroll=ft.ScrollMode.AUTO, height=500)


def mostrar_dialogo_eliminar(page: ft.Page, on_confirm):
    def cancelar(e):
        dlg.open = False
        page.update()

    def eliminar(e):
        dlg.open = False
        page.update()
        on_confirm() 

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar eliminación"),
        content=ft.Text("Esta acción es irreversible. ¿Está seguro de continuar?"),
        actions=[
            ft.TextButton("Cancelar", on_click=cancelar),
            ft.ElevatedButton(
                "Eliminar",
                bgcolor=ft.Colors.ERROR,
                color=ft.Colors.WHITE,
                on_click=eliminar,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        on_dismiss=cancelar,
    )

    page.overlay.append(dlg)
    dlg.open = True
    page.update()

def mostrar_dialogo_actualizar(page: ft.Page, on_confirm):
    def cancelar(e):
        dlg.open = False
        page.update()

    def confirmar(e):
        dlg.open = False
        page.update()
        on_confirm()  # 👈 Acción confirmada

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar cambios"),
        content=ft.Text("Los cambios se aplicarán de inmediato. ¿Desea continuar?"),
        actions=[
            ft.TextButton("Cancelar", on_click=cancelar),
            ft.ElevatedButton(
                "Confirmar",
                bgcolor=ft.Colors.PRIMARY,
                color=ft.Colors.WHITE,
                on_click=confirmar,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        on_dismiss=cancelar,
    )

    page.overlay.append(dlg)
    dlg.open = True
    page.update()
    
def dropdown_con_agregar(titulo: str, opciones: list[str], on_agregar, mostrar_agregar=True):
    items = [ft.dropdown.Option(valor) for valor in opciones]
    if mostrar_agregar:
        items.append(ft.dropdown.Option("+"))
    return ft.Dropdown(
        label=titulo,
        options=items,
        on_change=lambda e: on_agregar(e) if e.control.value == "+" else None
    )

