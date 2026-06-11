import os
from datetime import datetime
from typing import List
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from core.models import ResultadoAuditoria


VERDE = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
ROJO = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
GRIS = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
NEGRITA = Font(bold=True)
BORDE = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)

COLUMNAS = [
    "Archivo", "Proveedor", "Región", "Tipo", "Resultado",
    "Fecha Emisión", "Visita 1", "Visita 2",
    "Distribuidor", "Característica 1", "Característica 2", "Característica 3",
    "Tipo Entrega", "DNI", "Nombre", "Apellido", "Tipo Vínculo", "Firma",
    "Errores",
]


def _formato_fecha(d):
    return d.strftime("%d/%m/%Y") if d else ""


def generar_excel(resultados: List[ResultadoAuditoria], carpeta_salida: str) -> str:
    wb = Workbook()
    ws = wb.active
    ws.title = "Auditoría"

    # Encabezados
    for col, nombre in enumerate(COLUMNAS, start=1):
        celda = ws.cell(row=1, column=col, value=nombre)
        celda.font = NEGRITA
        celda.fill = GRIS
        celda.alignment = Alignment(horizontal="center")
        celda.border = BORDE

    # Datos
    for fila, r in enumerate(resultados, start=2):
        e = r.extraccion
        visita1 = _formato_fecha(e.visitas[0].fecha) if len(e.visitas) > 0 else ""
        visita2 = _formato_fecha(e.visitas[1].fecha) if len(e.visitas) > 1 else ""
        carac = e.caracteristicas_casa + [""] * (3 - len(e.caracteristicas_casa))
        errores_texto = "; ".join(f"{err.campo}: {err.mensaje}" for err in r.errores)

        valores = [
            r.archivo,
            r.proveedor,
            r.region,
            r.tipo_documento or "",
            "APROBADO" if r.aprobado else "RECHAZADO",
            _formato_fecha(e.fecha_emision),
            visita1,
            visita2,
            e.distribuidor or "",
            carac[0], carac[1], carac[2],
            e.tipo_entrega or "",
            e.dni or "",
            e.nombre or "",
            e.apellido or "",
            e.tipo_vinculo or "",
            "Sí" if e.tiene_firma else "No",
            errores_texto,
        ]

        fill = VERDE if r.aprobado else ROJO
        for col, valor in enumerate(valores, start=1):
            celda = ws.cell(row=fila, column=col, value=valor)
            celda.fill = fill
            celda.border = BORDE
            celda.alignment = Alignment(wrap_text=True)

    # Ancho de columnas
    anchos = [30, 12, 10, 14, 12, 14, 14, 14, 25, 20, 20, 20, 14, 14, 16, 16, 14, 8, 50]
    for col, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = ancho

    os.makedirs(carpeta_salida, exist_ok=True)
    nombre_archivo = f"auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    ruta = os.path.join(carpeta_salida, nombre_archivo)
    wb.save(ruta)
    return ruta
