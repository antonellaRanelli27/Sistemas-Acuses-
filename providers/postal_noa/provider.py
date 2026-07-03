from providers.base import BaseProvider
from providers.postal_noa.extractor import PostalNOAExtractor
from providers.postal_noa.validator import PostalNOAValidator
from core.models import ExtractionResult, ResultadoAuditoria


class PostalNOAProvider(BaseProvider):

    def __init__(self):
        self._extractor = PostalNOAExtractor()
        self._validator = PostalNOAValidator()

    @property
    def proveedor(self) -> str:
        return "POSTAL_NOA"

    @property
    def region(self) -> str:
        return "NOA"

    def obtener_texto(self, ruta_pdf: str, pdf_processor) -> str:
        return self._extractor.leer_pdf(ruta_pdf)

    def extraer(self, texto: str, ruta_pdf: str, pdf_processor=None) -> ExtractionResult:
        return self._extractor.extraer(texto, ruta_pdf, pdf_processor)

    def validar(self, extraccion: ExtractionResult) -> list:
        return self._validator.validar(extraccion)

    def procesar(self, archivo, texto, ruta_pdf, pdf_processor=None):
        extraccion = self.extraer(texto, ruta_pdf, pdf_processor)
        errores = self.validar(extraccion)
        return ResultadoAuditoria(
            archivo=archivo,
            proveedor=self.proveedor,
            region=self.region,
            tipo_documento=extraccion.tipo_documento,
            extraccion=extraccion,
            errores=errores,
        )
