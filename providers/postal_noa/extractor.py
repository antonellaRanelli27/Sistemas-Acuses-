import re
import fitz  # pymupdf
import numpy as np
from datetime import date
from typing import Optional, List, Tuple
from core.models import ExtractionResult, VisitData

VINCULOS_VALIDOS = {
    "titular", "hijo", "hija", "esposo", "esposa",
    "padre", "madre", "cónyuge", "conyuge", "familiar",
    "hermano", "hermana", "portero", "encargado",
}

VINCULOS_PATTERN = re.compile(
    r'\b(titular|hijo|hija|esposo|esposa|padre|madre|cónyuge|conyuge|familiar|hermano|hermana|portero|encargado)\b',
    re.IGNORECASE,
)

FEATURE_NOUNS = re.compile(
    r'\b(puerta|ventana|pared|portón|porton|techo|reja|frente|entrada|portería|porteria|escalera|balcón|balcon|garage)\b',
    re.IGNORECASE,
)

# Región de firma en el documento (x1%, y1%, x2%, y2%)
REG_FIRMA = (0.48, 0.55, 0.65, 0.90)


def _parsear_fecha(texto: str) -> Optional[date]:
    if not texto:
        return None
    m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', texto)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    return None


class PostalNOAExtractor:

    def leer_pdf(self, ruta_pdf: str) -> str:
        """Extrae texto directamente de la capa de texto del PDF."""
        doc = None
        try:
            doc = fitz.open(ruta_pdf)
            return "\n".join(page.get_text() for page in doc)
        except Exception:
            return ""
        finally:
            if doc:
                doc.close()

    def _detectar_firma(self, ruta_pdf: str, region: tuple) -> bool:
        """Detecta firma por densidad de píxeles oscuros en la región indicada usando fitz."""
        doc = None
        try:
            doc = fitz.open(ruta_pdf)
            page = doc[0]
            r = page.rect
            x1, y1, x2, y2 = region
            clip = fitz.Rect(x1 * r.width, y1 * r.height, x2 * r.width, y2 * r.height)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip, colorspace=fitz.csGRAY)
            arr = np.frombuffer(pix.samples, dtype=np.uint8)
            return np.sum(arr < 100) / len(arr) > 0.02
        except Exception:
            return False
        finally:
            if doc:
                doc.close()

    def _detectar_tipo(self, texto: str) -> Optional[str]:
        if re.search(r'Bajo\s+Firma', texto, re.IGNORECASE):
            return "bajo_firma"
        if re.search(r'bajo\s+puerta|2\s+visitas', texto, re.IGNORECASE):
            return "bajo_puerta"
        return None

    def _extraer_fecha_entrega(self, texto: str) -> Optional[date]:
        # Las etiquetas y valores están en columnas separadas, así que "Fecha:" no está
        # en la misma línea que el valor. Buscamos fecha+hora que NO esté seguida de ":"
        # (las notas de primera visita tienen "HH:MM: No responde...")
        fechas = re.findall(r'(\d{1,2}/\d{1,2}/\d{4})\s+\d{1,2}:\d{2}(?!\s*:)', texto)
        return _parsear_fecha(fechas[0]) if fechas else None

    def _extraer_primera_visita(self, texto: str) -> Optional[date]:
        # Patrón: "26/5/2026 11:00: No responde primer visita"
        m = re.search(
            r'(\d{1,2}/\d{1,2}/\d{4})\s+\d{1,2}:\d{2}:\s*No\s+responde',
            texto, re.IGNORECASE,
        )
        return _parsear_fecha(m.group(1)) if m else None

    def _extraer_vinculo(self, texto: str) -> str:
        m = VINCULOS_PATTERN.search(texto)
        return m.group(1).capitalize() if m else ""

    def _extraer_recibido_por(self, texto: str) -> Tuple[str, str, str]:
        """Retorna (nombre, apellido, dni).
        El campo 'Recibido por' tiene formato 'apellido nombre - DNI'.
        """
        m = re.search(
            r'([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+)+)\s{1,5}-\s{1,5}(\d{7,9})',
            texto, re.IGNORECASE,
        )
        if m:
            partes = m.group(1).strip().split()
            apellido = partes[0].capitalize() if partes else ""
            nombre = " ".join(p.capitalize() for p in partes[1:]) if len(partes) > 1 else ""
            return nombre, apellido, m.group(2).strip()
        return "", "", ""

    def _extraer_destinatario(self, texto: str) -> str:
        """
        Extrae el nombre del destinatario del documento.
        Formato en el PDF: 'APELLIDO, NOMBRE NOMBRE' en mayúsculas.
        """
        m = re.search(r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ]+,\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]+)$', texto, re.MULTILINE)
        if m:
            return m.group(1).strip()
        return ""

    def _extraer_caracteristicas(self, texto: str) -> List[str]:
        """
        Detecta características de la casa buscando sustantivos de casa en el texto.
        Cada sustantivo de casa inicia una nueva característica.
        """
        # Buscar línea que contenga características de casa
        m = re.search(
            r'\b(?:puerta|ventana|pared|portón|porton|techo|reja|frente|entrada|portería|porteria)\b.+',
            texto, re.IGNORECASE,
        )
        if not m:
            return []
        linea = m.group(0).strip()
        # Dividir la línea en cada sustantivo de casa (sin perder el primer elemento)
        partes = re.split(r'(?=\b(?:puerta|ventana|pared|portón|porton|techo|reja|frente|entrada|portería|porteria)\b)', linea, flags=re.IGNORECASE)
        return [p.strip() for p in partes if p.strip()]

    def extraer(self, texto: str, ruta_pdf: str, pdf_processor=None) -> ExtractionResult:
        texto_pdf = self.leer_pdf(ruta_pdf) if ruta_pdf else texto
        if not texto_pdf.strip():
            texto_pdf = texto

        tipo = self._detectar_tipo(texto_pdf)
        fecha_entrega = self._extraer_fecha_entrega(texto_pdf)
        nombre_cliente = self._extraer_destinatario(texto_pdf)

        visitas: List[VisitData] = []
        if tipo == "bajo_puerta":
            primera = self._extraer_primera_visita(texto_pdf)
            if primera:
                visitas.append(VisitData(fecha=primera, raw=str(primera)))
            if fecha_entrega:
                visitas.append(VisitData(fecha=fecha_entrega, raw=str(fecha_entrega)))
        elif fecha_entrega:
            visitas.append(VisitData(fecha=fecha_entrega, raw=str(fecha_entrega)))

        vinculo = ""
        nombre, apellido, dni = "", "", ""
        tiene_firma = False
        caracteristicas: List[str] = []

        if tipo == "bajo_firma":
            vinculo = self._extraer_vinculo(texto_pdf)
            nombre, apellido, dni = self._extraer_recibido_por(texto_pdf)
            tiene_firma = self._detectar_firma(ruta_pdf, REG_FIRMA)
        elif tipo == "bajo_puerta":
            caracteristicas = self._extraer_caracteristicas(texto_pdf)

        tipo_entrega = ""
        if tipo == "bajo_firma":
            tipo_entrega = "Bajo Firma"
        elif tipo == "bajo_puerta":
            tipo_entrega = "Bajo Puerta"

        return ExtractionResult(
            tipo_documento=tipo,
            fecha_emision=fecha_entrega,
            visitas=visitas,
            distribuidor=None,
            caracteristicas_casa=caracteristicas,
            tipo_entrega=tipo_entrega,
            dni=dni,
            nombre=nombre,
            apellido=apellido,
            tipo_vinculo=vinculo,
            tiene_firma=tiene_firma,
            nombre_cliente=nombre_cliente,
            texto_crudo=texto_pdf,
        )
