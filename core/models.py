from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date


@dataclass
class VisitData:
    fecha: Optional[date] = None
    raw: str = ""


@dataclass
class ExtractionResult:
    tipo_documento: Optional[str] = None       # "bajo_puerta" | "bajo_firma"
    fecha_emision: Optional[date] = None
    visitas: List[VisitData] = field(default_factory=list)
    distribuidor: Optional[str] = None
    caracteristicas_casa: List[str] = field(default_factory=list)
    tipo_entrega: Optional[str] = None
    # Campos exclusivos de bajo firma
    dni: Optional[str] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    tipo_vinculo: Optional[str] = None
    tiene_firma: bool = False
    nombre_cliente: Optional[str] = None   # nombre del cliente extraído del encabezado
    texto_crudo: str = ""


@dataclass
class ErrorValidacion:
    campo: str
    mensaje: str


@dataclass
class ResultadoAuditoria:
    archivo: str
    proveedor: str
    region: str
    tipo_documento: Optional[str]
    extraccion: ExtractionResult
    errores: List[ErrorValidacion] = field(default_factory=list)

    @property
    def aprobado(self) -> bool:
        return len(self.errores) == 0
