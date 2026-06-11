import re
from datetime import date
from typing import Optional, List
from core.models import ExtractionResult, VisitData

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def _parsear_fecha(texto: str) -> Optional[date]:
    # Formato DD/MM/YYYY o DD-MM-YYYY
    m = re.search(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})", texto)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d)
        except ValueError:
            pass

    # Formato DD de MMMM de YYYY
    m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", texto, re.IGNORECASE)
    if m:
        d, mo_str, y = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        mo = MESES.get(mo_str)
        if mo:
            try:
                return date(y, mo, d)
            except ValueError:
                pass

    return None


def _extraer_linea_despues_de(texto: str, etiqueta: str) -> str:
    """Devuelve el texto que sigue a una etiqueta en la misma línea o en la siguiente."""
    patron = re.compile(re.escape(etiqueta) + r"[:\s]*(.+)", re.IGNORECASE)
    m = patron.search(texto)
    return m.group(1).strip() if m else ""


def _extraer_bloque(texto: str, inicio: str, fin: str) -> str:
    """Extrae el bloque de texto entre dos etiquetas."""
    patron = re.compile(
        re.escape(inicio) + r"[:\s]*(.+?)\s*" + re.escape(fin),
        re.IGNORECASE | re.DOTALL,
    )
    m = patron.search(texto)
    return m.group(1).strip() if m else ""


class EMABANExtractor:

    # --- Etiquetas a ajustar según los documentos reales ---
    ETIQUETA_FECHA_EMISION = "Fecha de emisión"
    ETIQUETA_VISITA_1 = "1° visita"
    ETIQUETA_VISITA_2 = "2° visita"
    ETIQUETA_DISTRIBUIDOR = "Distribuidor"
    ETIQUETA_CARACTERISTICA_1 = "Característica 1"
    ETIQUETA_CARACTERISTICA_2 = "Característica 2"
    ETIQUETA_CARACTERISTICA_3 = "Característica 3"
    ETIQUETA_TIPO_ENTREGA = "Tipo de entrega"
    ETIQUETA_DNI = "DNI"
    ETIQUETA_NOMBRE = "Nombre"
    ETIQUETA_APELLIDO = "Apellido"
    ETIQUETA_VINCULO = "Tipo de vínculo"

    # Región de la firma: (x%, y%, ancho%, alto%) del tamaño de la página
    # Ajustar con los documentos reales
    REGION_FIRMA = (0.55, 0.75, 0.35, 0.15)

    def _detectar_tipo(self, texto: str) -> Optional[str]:
        texto_lower = texto.lower()
        if "bajo puerta" in texto_lower:
            return "bajo_puerta"
        if "bajo firma" in texto_lower:
            return "bajo_firma"
        return None

    def _extraer_visitas(self, texto: str, cantidad: int) -> List[VisitData]:
        visitas = []
        etiquetas = [self.ETIQUETA_VISITA_1, self.ETIQUETA_VISITA_2]
        for i in range(cantidad):
            raw = _extraer_linea_despues_de(texto, etiquetas[i])
            visitas.append(VisitData(fecha=_parsear_fecha(raw), raw=raw))
        return visitas

    def extraer(self, texto: str, ruta_pdf: str, pdf_processor=None) -> ExtractionResult:
        tipo = self._detectar_tipo(texto)
        fecha_emision_raw = _extraer_linea_despues_de(texto, self.ETIQUETA_FECHA_EMISION)

        if tipo == "bajo_puerta":
            visitas = self._extraer_visitas(texto, 2)
        elif tipo == "bajo_firma":
            visitas = self._extraer_visitas(texto, 1)
        else:
            visitas = []

        caracteristicas = [
            _extraer_linea_despues_de(texto, self.ETIQUETA_CARACTERISTICA_1),
            _extraer_linea_despues_de(texto, self.ETIQUETA_CARACTERISTICA_2),
            _extraer_linea_despues_de(texto, self.ETIQUETA_CARACTERISTICA_3),
        ]
        caracteristicas = [c for c in caracteristicas if c]

        tiene_firma = False
        if tipo == "bajo_firma" and pdf_processor:
            tiene_firma = pdf_processor.tiene_firma_en_region(ruta_pdf, self.REGION_FIRMA)

        return ExtractionResult(
            tipo_documento=tipo,
            fecha_emision=_parsear_fecha(fecha_emision_raw),
            visitas=visitas,
            distribuidor=_extraer_linea_despues_de(texto, self.ETIQUETA_DISTRIBUIDOR),
            caracteristicas_casa=caracteristicas,
            tipo_entrega=_extraer_linea_despues_de(texto, self.ETIQUETA_TIPO_ENTREGA),
            dni=_extraer_linea_despues_de(texto, self.ETIQUETA_DNI),
            nombre=_extraer_linea_despues_de(texto, self.ETIQUETA_NOMBRE),
            apellido=_extraer_linea_despues_de(texto, self.ETIQUETA_APELLIDO),
            tipo_vinculo=_extraer_linea_despues_de(texto, self.ETIQUETA_VINCULO),
            tiene_firma=tiene_firma,
            texto_crudo=texto,
        )
