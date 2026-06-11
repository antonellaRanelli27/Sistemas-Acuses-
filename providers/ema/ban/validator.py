from datetime import date
from typing import List
from core.models import ExtractionResult, ErrorValidacion

DIAS_NO_VALIDOS = {5: "sábado", 6: "domingo"}


def _es_dia_valido(d: date) -> bool:
    return d.weekday() not in DIAS_NO_VALIDOS


def _nombre_dia(d: date) -> str:
    return DIAS_NO_VALIDOS.get(d.weekday(), "")


def _validar_visita_posterior(visita, fecha_emision: date, etiqueta: str) -> List[ErrorValidacion]:
    errores = []
    if visita.fecha is None:
        errores.append(ErrorValidacion(etiqueta, "No se pudo leer la fecha de la visita"))
        return errores
    if visita.fecha <= fecha_emision:
        errores.append(ErrorValidacion(
            etiqueta,
            f"La visita ({visita.fecha:%d/%m/%Y}) debe ser posterior a la fecha de emisión ({fecha_emision:%d/%m/%Y})"
        ))
    if not _es_dia_valido(visita.fecha):
        errores.append(ErrorValidacion(
            etiqueta,
            f"La visita cae en {_nombre_dia(visita.fecha)} ({visita.fecha:%d/%m/%Y}), debe ser día hábil"
        ))
    return errores


class EMABANValidator:

    def validar_bajo_puerta(self, e: ExtractionResult) -> List[ErrorValidacion]:
        errores = []

        if e.fecha_emision is None:
            errores.append(ErrorValidacion("Fecha de emisión", "No se pudo leer la fecha de emisión"))
            return errores

        if len(e.visitas) < 2:
            errores.append(ErrorValidacion("Visitas", f"Se requieren 2 visitas, se encontraron {len(e.visitas)}"))
        else:
            errores += _validar_visita_posterior(e.visitas[0], e.fecha_emision, "1° visita")
            errores += _validar_visita_posterior(e.visitas[1], e.fecha_emision, "2° visita")

        if not e.distribuidor:
            errores.append(ErrorValidacion("Distribuidor", "No se encontraron los datos del distribuidor"))

        if len(e.caracteristicas_casa) < 3:
            errores.append(ErrorValidacion(
                "Características de la casa",
                f"Se requieren 3 características, se encontraron {len(e.caracteristicas_casa)}"
            ))

        if not e.tipo_entrega:
            errores.append(ErrorValidacion("Tipo de entrega", "No se encontró el tipo de entrega"))
        elif "bajo puerta" not in e.tipo_entrega.lower():
            errores.append(ErrorValidacion(
                "Tipo de entrega",
                f"Debe decir 'bajo puerta', se encontró: '{e.tipo_entrega}'"
            ))

        return errores

    def validar_bajo_firma(self, e: ExtractionResult) -> List[ErrorValidacion]:
        errores = []

        if e.fecha_emision is None:
            errores.append(ErrorValidacion("Fecha de emisión", "No se pudo leer la fecha de emisión"))
            return errores

        if len(e.visitas) < 1:
            errores.append(ErrorValidacion("Visitas", "Se requiere al menos 1 visita"))
        else:
            errores += _validar_visita_posterior(e.visitas[0], e.fecha_emision, "1° visita")

        if not e.distribuidor:
            errores.append(ErrorValidacion("Distribuidor", "No se encontraron los datos del distribuidor"))

        if not e.dni:
            errores.append(ErrorValidacion("DNI", "No se encontró el DNI del firmante"))
        if not e.nombre:
            errores.append(ErrorValidacion("Nombre", "No se encontró el nombre del firmante"))
        if not e.apellido:
            errores.append(ErrorValidacion("Apellido", "No se encontró el apellido del firmante"))

        if not e.tipo_vinculo:
            errores.append(ErrorValidacion("Tipo de vínculo", "No se encontró el tipo de vínculo"))
        elif "vecino" in e.tipo_vinculo.lower():
            errores.append(ErrorValidacion(
                "Tipo de vínculo",
                f"El vínculo 'vecino' no corresponde (se encontró: '{e.tipo_vinculo}')"
            ))

        if len(e.caracteristicas_casa) < 3:
            errores.append(ErrorValidacion(
                "Características de la casa",
                f"Se requieren 3 características, se encontraron {len(e.caracteristicas_casa)}"
            ))

        if not e.tiene_firma:
            errores.append(ErrorValidacion("Firma", "No se detectó firma digitalizada en el documento"))

        return errores

    def validar(self, e: ExtractionResult) -> List[ErrorValidacion]:
        if e.tipo_documento == "bajo_puerta":
            return self.validar_bajo_puerta(e)
        if e.tipo_documento == "bajo_firma":
            return self.validar_bajo_firma(e)
        return [ErrorValidacion("Tipo de documento", "No se pudo determinar si es bajo puerta o bajo firma")]
