import re
from datetime import date
from typing import Optional, List
from core.models import ExtractionResult, VisitData

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# ─────────────────────────────────────────────────────────────────
# Regiones del documento EMA (x1%, y1%, x2%, y2%)
#
# Layout real confirmado con OCR:
#   0–28%   → Encabezado completo + fila de headers VISITA + fila de fechas
#   28–52%  → Cuerpo de visitas (hora, distribuidor) + DNI/nombre/vínculo (bajo firma)
#   52–78%  → Fotos, mapa (no se usa para extracción de texto)
#
# Columna izq (0–50%): 1ª VISITA  |  Columna der (50–100%): 2ª VISITA
# ─────────────────────────────────────────────────────────────────
REG_HEADER   = (0.00, 0.00, 1.00, 0.28)   # Encabezado + fila de fechas de visita
REG_VISITA_1 = (0.00, 0.25, 0.50, 0.50)   # Izq: hora, distribuidor, DNI, nombre, vínculo
REG_VISITA_2 = (0.50, 0.25, 1.00, 0.50)   # Der: hora, distribuidor, tipo entrega, referencias
REG_FIRMA_IMG = (0.48, 0.55, 1.00, 0.78)  # Imagen de la firma digitalizada


def _parsear_fecha(texto: str) -> Optional[date]:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", texto)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    m = re.search(r"(\d{1,2})[/\.](\d{1,2})[/\.](\d{2,4})", texto)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d)
        except ValueError:
            pass
    m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", texto, re.IGNORECASE)
    if m:
        mo = MESES.get(m.group(2).lower())
        if mo:
            try:
                return date(int(m.group(3)), mo, int(m.group(1)))
            except ValueError:
                pass
    return None


def _extraer_referencias(texto: str) -> List[str]:
    refs = []
    for n in ["1", "2", "3"]:
        m = re.search(
            rf"\b{n}\s*[°ª*\"'\?\.]\s*REFERENCIA\s*[:\.\s]+(.+)",
            texto, re.IGNORECASE,
        )
        if m:
            refs.append(m.group(1).strip().rstrip("."))
    return refs


EXCLUIR_VISITA = [
    r"Descripci[oó]n\s+NO",
    r"Se\s+mud[oó]",
    r"Rehusado",
    r"Otros",
    r"^\d{1,2}:\d{2}",     # hora
    r"REFERENCIA",
    r"^[-–]+$",
]


class EMABANExtractor:

    def _detectar_tipo(self, txt_visita2: str) -> Optional[str]:
        t = txt_visita2.lower()
        if re.search(r"bajo\s+puer", t):
            return "bajo_puerta"
        if re.search(r"f[iu]rmad", t):
            return "bajo_firma"
        return None

    def _fechas_de_visitas(self, txt_header: str) -> List[Optional[date]]:
        """
        Busca TODAS las ocurrencias de 'VISITA' en el header y extrae
        la primera fecha que aparece después de cada una.
        """
        lineas = txt_header.splitlines()
        fechas = []
        for i, linea in enumerate(lineas):
            if re.search(r"\bVISITA\b", linea, re.IGNORECASE):
                for j in range(i + 1, min(i + 6, len(lineas))):
                    f = _parsear_fecha(lineas[j])
                    if f:
                        fechas.append(f)
                        break
        return fechas

    def _distribuidor(self, txt_visita1: str) -> str:
        m = re.search(r"\d{4,}\s*[-–]\s*[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑA-Za-z ]+", txt_visita1)
        return m.group(0).strip() if m else ""

    def _datos_firmante(self, txt_visita1: str):
        """
        Extrae DNI, nombre, apellido y vínculo del área izquierda de la visita.
        Orden esperado en el doc EMA: Hora → Distribuidor → [DNI label] → DNI nro
        → Aclaración (nombre) → Vínculo.
        """
        dni, nombre, apellido, vinculo = "", "", "", ""
        lineas = [l.strip() for l in txt_visita1.splitlines()]
        excluir = EXCLUIR_VISITA + [r"\d{4,}\s*[-–]", r"^\d{4}-\d{2}-\d{2}$"]

        # DNI: primera línea que sea exactamente 7-8 dígitos
        dni_idx = -1
        for i, l in enumerate(lineas):
            if re.fullmatch(r"\d{7,8}", l):
                dni = l
                dni_idx = i
                break

        if dni_idx >= 0:
            # Nombre: primera línea de solo letras y espacios después del DNI
            for j in range(dni_idx + 1, min(dni_idx + 6, len(lineas))):
                l = lineas[j]
                if (l
                        and not re.search(r"\d", l)
                        and not any(re.search(p, l, re.IGNORECASE) for p in excluir)
                        and re.match(r"^[A-ZÁÉÍÓÚÑa-záéíóúñ ]+$", l)):
                    partes = l.split(maxsplit=1)
                    nombre = partes[0]
                    apellido = partes[1] if len(partes) > 1 else ""
                    # Vínculo: siguiente línea de texto válida
                    for k in range(j + 1, min(j + 4, len(lineas))):
                        v = lineas[k]
                        if (v and not re.search(r"\d", v)
                                and not any(re.search(p, v, re.IGNORECASE) for p in excluir)
                                and re.match(r"^[A-ZÁÉÍÓÚÑa-záéíóúñ ]+$", v)):
                            vinculo = v
                            break
                    break

        return dni, nombre, apellido, vinculo

    def extraer(self, texto: str, ruta_pdf: str, pdf_processor=None) -> ExtractionResult:
        def reg(region):
            if pdf_processor:
                return pdf_processor.extraer_texto_region(ruta_pdf, region)
            return texto

        txt_header  = reg(REG_HEADER)
        txt_visita1 = reg(REG_VISITA_1)
        txt_visita2 = reg(REG_VISITA_2)

        # Tipo de documento (desde columna derecha donde aparece Tipo de Entrega)
        tipo = self._detectar_tipo(txt_visita2)

        # Fecha de emisión
        m = re.search(r"Emisi[oó]n[:\s]+(\d{4}-\d{2}-\d{2})", txt_header, re.IGNORECASE)
        fecha_emision = _parsear_fecha(m.group(1)) if m else None

        # Fechas de visitas (línea posterior al encabezado VISITA en el header)
        fechas_visitas = self._fechas_de_visitas(txt_header)

        visita1 = VisitData(
            fecha=fechas_visitas[0] if len(fechas_visitas) > 0 else None,
            raw=str(fechas_visitas[0]) if len(fechas_visitas) > 0 else "",
        )
        visitas = [visita1]

        if tipo == "bajo_puerta" and len(fechas_visitas) > 1:
            visitas.append(VisitData(
                fecha=fechas_visitas[1],
                raw=str(fechas_visitas[1]),
            ))

        # Distribuidor
        distribuidor = self._distribuidor(txt_visita1)

        # Tipo de entrega (texto)
        tipo_entrega = ""
        m = re.search(r"Tipo\s+de\s+Entrega\s*\n(.+)", txt_visita2, re.IGNORECASE)
        if m:
            tipo_entrega = m.group(1).strip()
        else:
            # Buscar "Bajo Puerta" o "Firmada" directo en el texto
            m2 = re.search(r"(Bajo\s+Puer\w*|F[iu]rmad\w*)", txt_visita2, re.IGNORECASE)
            tipo_entrega = m2.group(1).strip() if m2 else ""

        # Referencias / características
        caracteristicas = _extraer_referencias(txt_visita2)

        # Datos del firmante (bajo firma)
        dni, nombre, apellido, tipo_vinculo = "", "", "", ""
        if tipo == "bajo_firma":
            dni, nombre, apellido, tipo_vinculo = self._datos_firmante(txt_visita1)

        # Firma digitalizada
        tiene_firma = False
        if tipo == "bajo_firma" and pdf_processor:
            tiene_firma = pdf_processor.tiene_firma_en_region(ruta_pdf, REG_FIRMA_IMG)

        return ExtractionResult(
            tipo_documento=tipo,
            fecha_emision=fecha_emision,
            visitas=visitas,
            distribuidor=distribuidor,
            caracteristicas_casa=caracteristicas,
            tipo_entrega=tipo_entrega,
            dni=dni,
            nombre=nombre,
            apellido=apellido,
            tipo_vinculo=tipo_vinculo,
            tiene_firma=tiene_firma,
            texto_crudo=texto,
        )
