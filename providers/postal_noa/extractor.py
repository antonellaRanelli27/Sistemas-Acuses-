import re
import pdfplumber
from datetime import date
from typing import Optional, List, Tuple
from core.models import ExtractionResult, VisitData

VINCULOS_VALIDOS = {
    "titular", "hijo", "hija", "esposo", "esposa",
    "padre", "madre", "cónyuge", "conyuge", "familiar",
    "hermano", "hermana",
}

VINCULOS_PATTERN = re.compile(
    r'\b(titular|hijo|hija|esposo|esposa|padre|madre|cónyuge|conyuge|familiar|hermano|hermana)\b',
    re.IGNORECASE,
)

FEATURE_NOUNS = re.compile(
    r'\b(puerta|ventana|pared|portón|porton|techo|reja|frente|entrada|portería|porteria|escalera|balcón|balcon|garage)\b',
    re.IGNORECASE,
)

# Región de firma en el documento (x1%, y1%, x2%, y2%)
REG_FIRMA = (0.33, 0.48, 0.63, 0.82)


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
        try:
            with pdfplumber.open(ruta_pdf) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception:
            return ""

    def _detectar_tipo(self, texto: str) -> Optional[str]:
        if re.search(r'Bajo\s+Firma', texto, re.IGNORECASE):
            return "bajo_firma"
        if re.search(r'bajo\s+puerta|2\s+visitas', texto, re.IGNORECASE):
            return "bajo_puerta"
        return None

    def _extraer_fecha_entrega(self, texto: str) -> Optional[date]:
        # Buscar "Fecha: DD/MM/YYYY"
        m = re.search(r'Fecha:\s*(\d{1,2}/\d{1,2}/\d{4})', texto, re.IGNORECASE)
        if m:
            return _parsear_fecha(m.group(1))
        # Buscar fecha con hora que NO está seguida de ":" (las notas tienen "HH:MM: No responde...")
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
        """Retorna (nombre, apellido, dni) del campo Recibido por."""
        m = re.search(
            r'Recibido\s+por:\s*([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+)*)\s*-\s*(\d{7,9})',
            texto, re.IGNORECASE,
        )
        if m:
            partes = m.group(1).strip().split()
            nombre = partes[0] if partes else ""
            apellido = " ".join(partes[1:]) if len(partes) > 1 else ""
            return nombre, apellido, m.group(2).strip()
        return "", "", ""

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
            if pdf_processor:
                tiene_firma = pdf_processor.tiene_firma_en_region(ruta_pdf, REG_FIRMA)
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
            texto_crudo=texto_pdf,
        )
