from datetime import date
from typing import List
from core.models import ExtractionResult, ErrorValidacion
from providers.postal_noa.extractor import VINCULOS_VALIDOS

DIAS_NO_VALIDOS = {5: "sábado", 6: "domingo"}


def _es_dia_valido(d: date) -> bool:
    return d.weekday() not in DIAS_NO_VALIDOS


def _nombre_dia(d: date) -> str:
    return DIAS_NO_VALIDOS.get(d.weekday(), "")


class PostalNOAValidator:

    def validar_bajo_firma(self, e: ExtractionResult) -> List[ErrorValidacion]:
        errores = []

        if not e.visitas or e.visitas[0].fecha is None:
            errores.append(ErrorValidacion("Fecha", "No se pudo leer la fecha de entrega"))
            return errores

        fecha = e.visitas[0].fecha
        if not _es_dia_valido(fecha):
            errores.append(ErrorValidacion(
                "Fecha",
                f"La entrega cae en {_nombre_dia(fecha)} ({fecha:%d/%m/%Y}), debe ser día hábil"
            ))

        if not e.dni:
            errores.append(ErrorValidacion("DNI", "No se encontró el DNI del receptor"))

        if not e.nombre and not e.apellido:
            errores.append(ErrorValidacion("Recibido por", "No se encontró nombre del receptor"))

        if not e.tipo_vinculo:
            errores.append(ErrorValidacion("Vínculo", "No se encontró el tipo de vínculo"))
        elif e.tipo_vinculo.lower().replace("ó", "o") not in VINCULOS_VALIDOS:
            errores.append(ErrorValidacion(
                "Vínculo",
                f"Vínculo no permitido: '{e.tipo_vinculo}'. Permitidos: {', '.join(sorted(VINCULOS_VALIDOS))}"
            ))

        if not e.tiene_firma:
            errores.append(ErrorValidacion("Firma", "No se detectó firma digitalizada en el documento"))

        # Recibido por vs. nombre del destinatario
        if e.nombre_cliente and (e.nombre or e.apellido):
            palabras_cliente = {p.strip(',') for p in e.nombre_cliente.upper().split()}
            palabras_firmante = set(f"{e.nombre} {e.apellido}".upper().split())
            if not palabras_firmante & palabras_cliente:
                errores.append(ErrorValidacion(
                    "Recibido por",
                    f"Ninguna palabra de '{e.nombre} {e.apellido}' coincide con el destinatario ('{e.nombre_cliente}')"
                ))

        return errores

    def validar_bajo_puerta(self, e: ExtractionResult) -> List[ErrorValidacion]:
        errores = []

        if len(e.visitas) < 2:
            errores.append(ErrorValidacion(
                "Visitas",
                f"Se requieren 2 visitas, se encontraron {len(e.visitas)}"
            ))
        else:
            v1, v2 = e.visitas[0], e.visitas[1]

            if v1.fecha is None:
                errores.append(ErrorValidacion("1° visita", "No se pudo leer la fecha de la primera visita"))
            else:
                if not _es_dia_valido(v1.fecha):
                    errores.append(ErrorValidacion(
                        "1° visita",
                        f"La primera visita cae en {_nombre_dia(v1.fecha)} ({v1.fecha:%d/%m/%Y}), debe ser día hábil"
                    ))

            if v2.fecha is None:
                errores.append(ErrorValidacion("2° visita", "No se pudo leer la fecha de entrega"))
            else:
                if not _es_dia_valido(v2.fecha):
                    errores.append(ErrorValidacion(
                        "2° visita",
                        f"La entrega cae en {_nombre_dia(v2.fecha)} ({v2.fecha:%d/%m/%Y}), debe ser día hábil"
                    ))

            if v1.fecha and v2.fecha and v1.fecha >= v2.fecha:
                errores.append(ErrorValidacion(
                    "Visitas",
                    f"La primera visita ({v1.fecha:%d/%m/%Y}) debe ser anterior a la entrega ({v2.fecha:%d/%m/%Y})"
                ))

        if len(e.caracteristicas_casa) < 3:
            errores.append(ErrorValidacion(
                "Características de la casa",
                f"Se requieren 3 características, se encontraron {len(e.caracteristicas_casa)}"
            ))

        return errores

    def validar(self, e: ExtractionResult) -> List[ErrorValidacion]:
        if e.tipo_documento == "bajo_firma":
            return self.validar_bajo_firma(e)
        if e.tipo_documento == "bajo_puerta":
            return self.validar_bajo_puerta(e)
        return [ErrorValidacion("Tipo de documento", "No se pudo determinar si es bajo puerta o bajo firma")]
