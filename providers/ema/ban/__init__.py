from providers.base import BaseProvider
from providers.ema.ban.extractor import EMABANExtractor
from providers.ema.ban.validator import EMABANValidator
from core.models import ExtractionResult


class EMABANProvider(BaseProvider):

    def __init__(self):
        self._extractor = EMABANExtractor()
        self._validator = EMABANValidator()

    @property
    def proveedor(self) -> str:
        return "EMA"

    @property
    def region(self) -> str:
        return "BAN"

    def extraer(self, texto: str, ruta_pdf: str, pdf_processor=None) -> ExtractionResult:
        return self._extractor.extraer(texto, ruta_pdf, pdf_processor)

    def validar(self, extraccion: ExtractionResult) -> list:
        return self._validator.validar(extraccion)

    def procesar(self, archivo, texto, ruta_pdf, pdf_processor=None):
        extraccion = self.extraer(texto, ruta_pdf, pdf_processor)
        errores = self.validar(extraccion)
        from core.models import ResultadoAuditoria
        return ResultadoAuditoria(
            archivo=archivo,
            proveedor=self.proveedor,
            region=self.region,
            tipo_documento=extraccion.tipo_documento,
            extraccion=extraccion,
            errores=errores,
        )
