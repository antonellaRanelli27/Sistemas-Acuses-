from abc import ABC, abstractmethod
from core.models import ExtractionResult, ResultadoAuditoria


class BaseProvider(ABC):

    @property
    @abstractmethod
    def proveedor(self) -> str:
        pass

    @property
    @abstractmethod
    def region(self) -> str:
        pass

    @abstractmethod
    def extraer(self, texto: str, ruta_pdf: str) -> ExtractionResult:
        """Extrae los campos del texto OCR y del PDF si hace falta."""
        pass

    @abstractmethod
    def validar(self, extraccion: ExtractionResult) -> list:
        """Devuelve una lista de ErrorValidacion."""
        pass

    def obtener_texto(self, ruta_pdf: str, pdf_processor) -> str:
        """Extrae el texto del PDF. Por defecto usa OCR; sobreescribir para PDF con capa de texto."""
        return pdf_processor.extraer_texto(ruta_pdf)

    def procesar(self, archivo: str, texto: str, ruta_pdf: str) -> ResultadoAuditoria:
        extraccion = self.extraer(texto, ruta_pdf)
        errores = self.validar(extraccion)
        return ResultadoAuditoria(
            archivo=archivo,
            proveedor=self.proveedor,
            region=self.region,
            tipo_documento=extraccion.tipo_documento,
            extraccion=extraccion,
            errores=errores,
        )
