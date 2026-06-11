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
    # YYYY-MM-DD (formato del documento EMA)
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", texto)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d)
        except ValueError:
            pass

    # DD/MM/YYYY o DD-MM-YYYY
    m = re.search(r"(\d{1,2})[/\.](\d{1,2})[/\.](\d{2,4})", texto)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d)
        except ValueError:
            pass

    # DD de MMMM de YYYY
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


def _valor_despues_de(texto: str, etiqueta: str) -> str:
    """
    Busca una etiqueta y devuelve el valor en la misma línea (etiqueta: valor)
    o en la línea siguiente si la etiqueta está sola.
    """
    patron_misma_linea = re.compile(
        re.escape(etiqueta) + r"[:\s]+(.+)", re.IGNORECASE
    )
    m = patron_misma_linea.search(texto)
    if m:
        valor = m.group(1).strip()
        if valor:
            return valor

    # Busca en la línea siguiente
    lineas = texto.splitlines()
    for i, linea in enumerate(lineas):
        if re.search(re.escape(etiqueta), linea, re.IGNORECASE):
            for j in range(i + 1, min(i + 4, len(lineas))):
                siguiente = lineas[j].strip()
                if siguiente:
                    return siguiente
    return ""


def _extraer_seccion(texto: str, inicio: str, fin: str) -> str:
    """Extrae el bloque de texto entre dos patrones."""
    patron = re.compile(
        r"(?:" + inicio + r")(.*?)(?:" + fin + r"|$)",
        re.IGNORECASE | re.DOTALL,
    )
    m = patron.search(texto)
    return m.group(1).strip() if m else ""


def _normalizar_visita(label: str) -> str:
    """Normaliza variaciones OCR de 1ª/2ª VISITA."""
    return label.replace("1ª", "1").replace("2ª", "2").replace("1a", "1").replace("2a", "2")


class EMABANExtractor:

    # Región de firma: (x%, y%, ancho%, alto%) relativo al tamaño de la página
    # Ajustar si el área de firma cambia de posición
    REGION_FIRMA = (0.05, 0.45, 0.40, 0.12)

    def _detectar_tipo(self, texto: str) -> Optional[str]:
        m = re.search(r"Tipo\s+de\s+Entrega[:\s]+(\S+(?:\s+\S+)?)", texto, re.IGNORECASE)
        if m:
            valor = m.group(1).strip().lower()
            if "puerta" in valor:
                return "bajo_puerta"
            if "firma" in valor:
                return "bajo_firma"
        # fallback por presencia de texto
        texto_lower = texto.lower()
        if "bajo puerta" in texto_lower:
            return "bajo_puerta"
        if "bajo firma" in texto_lower:
            return "bajo_firma"
        return None

    def _extraer_fecha_visita(self, texto: str, numero: int) -> VisitData:
        """
        Extrae la fecha de la sección Nª VISITA.
        Soporta variaciones OCR: 1ª, 1a, 1°, 1ra.
        """
        patrones_inicio = [
            rf"{numero}[aª°]?\s*VISITA",
            rf"{numero}ra?\s*VISITA",
        ]
        siguiente_seccion = [
            r"[2-9][aª°]?\s*VISITA",
            r"D\.?N\.?I",
            r"Referencias",
            r"Descripci",
        ]
        fin = "|".join(siguiente_seccion)

        seccion = ""
        for pat in patrones_inicio:
            seccion = _extraer_seccion(texto, pat, fin)
            if seccion:
                break

        if not seccion:
            return VisitData()

        raw = _valor_despues_de(seccion, "Fecha")
        return VisitData(fecha=_parsear_fecha(raw or seccion), raw=raw)

    def _extraer_distribuidor(self, texto: str) -> str:
        """Toma el distribuidor de la 2ª visita, o de la 1ª si no hay 2ª."""
        for numero in [2, 1]:
            patrones = [rf"{numero}[aª°]?\s*VISITA", rf"{numero}ra?\s*VISITA"]
            fin = r"D\.?N\.?I|Referencias|Descripci|$"
            for pat in patrones:
                seccion = _extraer_seccion(texto, pat, fin)
                if seccion:
                    valor = _valor_despues_de(seccion, "Distribuidor")
                    if valor:
                        return valor
        return _valor_despues_de(texto, "Distribuidor")

    def _extraer_referencias(self, texto: str) -> List[str]:
        refs = []
        for n in ["1", "2", "3"]:
            # Busca "1° REFERENCIA: valor" o "1ª REFERENCIA: valor"
            m = re.search(
                rf"{n}[°ª]?\s*REFERENCIA[:\s]+(.+)",
                texto,
                re.IGNORECASE,
            )
            if m:
                refs.append(m.group(1).strip())
        return refs

    def extraer(self, texto: str, ruta_pdf: str, pdf_processor=None) -> ExtractionResult:
        tipo = self._detectar_tipo(texto)

        fecha_emision_raw = _valor_despues_de(texto, "Emisión")
        # Evitar que tome "Fecha vencimiento" como emisión
        emision_match = re.search(r"Emisi[oó]n[:\s]+(\d{4}-\d{2}-\d{2}|\d{1,2}[/\.]\d{1,2}[/\.]\d{2,4})", texto, re.IGNORECASE)
        if emision_match:
            fecha_emision_raw = emision_match.group(1)

        visita1 = self._extraer_fecha_visita(texto, 1)
        visita2 = self._extraer_fecha_visita(texto, 2) if tipo == "bajo_puerta" else VisitData()

        visitas = [visita1]
        if tipo == "bajo_puerta" and visita2.raw:
            visitas.append(visita2)

        tipo_entrega_raw = _valor_despues_de(texto, "Tipo de Entrega")

        tiene_firma = False
        if tipo == "bajo_firma" and pdf_processor:
            tiene_firma = pdf_processor.tiene_firma_en_region(ruta_pdf, self.REGION_FIRMA)

        # Aclaración = nombre completo del firmante en documentos EMA
        aclaracion = _valor_despues_de(texto, "Aclaración")
        nombre, apellido = "", ""
        if aclaracion:
            partes = aclaracion.split(maxsplit=1)
            nombre = partes[0] if partes else aclaracion
            apellido = partes[1] if len(partes) > 1 else ""

        return ExtractionResult(
            tipo_documento=tipo,
            fecha_emision=_parsear_fecha(fecha_emision_raw),
            visitas=visitas,
            distribuidor=self._extraer_distribuidor(texto),
            caracteristicas_casa=self._extraer_referencias(texto),
            tipo_entrega=tipo_entrega_raw,
            dni=_valor_despues_de(texto, "D.N.I"),
            nombre=nombre,
            apellido=apellido,
            tipo_vinculo=_valor_despues_de(texto, "Vínculo"),
            tiene_firma=tiene_firma,
            texto_crudo=texto,
        )
