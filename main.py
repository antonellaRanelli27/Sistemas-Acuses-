import os
import sys
import argparse
from core.pdf_processor import PDFProcessor
from core.reporter import generar_excel
import config

PROVIDERS = {
    ("EMA", "BAN"): "providers.ema.ban.EMABANProvider",
}


def cargar_provider(proveedor: str, region: str):
    clave = (proveedor.upper(), region.upper())
    if clave not in PROVIDERS:
        disponibles = ", ".join(f"{p}/{r}" for p, r in PROVIDERS)
        print(f"[ERROR] Proveedor/región '{proveedor}/{region}' no está configurado.")
        print(f"        Disponibles: {disponibles}")
        sys.exit(1)
    modulo_path, clase = PROVIDERS[clave].rsplit(".", 1)
    modulo = __import__(modulo_path, fromlist=[clase])
    return getattr(modulo, clase)()


def procesar(proveedor: str, region: str, carpeta_entrada: str, carpeta_salida: str):
    provider = cargar_provider(proveedor, region)
    processor = PDFProcessor()

    pdfs = [f for f in os.listdir(carpeta_entrada) if f.lower().endswith(".pdf")]
    if not pdfs:
        print(f"[AVISO] No se encontraron PDFs en '{carpeta_entrada}'")
        return

    print(f"Procesando {len(pdfs)} archivo(s) para {proveedor}/{region}...\n")
    resultados = []

    for nombre in pdfs:
        ruta = os.path.join(carpeta_entrada, nombre)
        print(f"  → {nombre}", end=" ", flush=True)
        try:
            texto = processor.extraer_texto(ruta)
            resultado = provider.procesar(nombre, texto, ruta, processor)
            estado = "APROBADO ✓" if resultado.aprobado else f"RECHAZADO ({len(resultado.errores)} error/es)"
            print(estado)
            if not resultado.aprobado:
                for err in resultado.errores:
                    print(f"       • {err.campo}: {err.mensaje}")
            resultados.append(resultado)
        except Exception as ex:
            print(f"ERROR al procesar: {ex}")

    ruta_excel = generar_excel(resultados, carpeta_salida)
    print(f"\nReporte generado: {ruta_excel}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sistema de auditoría de acuses")
    parser.add_argument("--proveedor", default="EMA", help="Código del proveedor (ej: EMA)")
    parser.add_argument("--region", default="BAN", help="Código de región (ej: BAN)")
    parser.add_argument("--entrada", default=config.INPUT_FOLDER, help="Carpeta con los PDFs")
    parser.add_argument("--salida", default=config.OUTPUT_FOLDER, help="Carpeta para el Excel")
    args = parser.parse_args()

    procesar(args.proveedor, args.region, args.entrada, args.salida)
