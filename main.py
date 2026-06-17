import os
import sys
import shutil
import argparse
from datetime import datetime
from core.pdf_processor import PDFProcessor
from core.reporter import actualizar_excel
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


def procesar(proveedor: str, region: str):
    provider = cargar_provider(proveedor, region)
    processor = PDFProcessor()

    carpeta_proveedor = os.path.join(config.BASE_DIR, proveedor.upper())
    carpeta_pendientes = os.path.join(carpeta_proveedor, "pendientes")
    carpeta_procesados = os.path.join(carpeta_proveedor, "procesados")
    carpeta_errores    = os.path.join(carpeta_proveedor, "errores")

    os.makedirs(carpeta_pendientes, exist_ok=True)
    os.makedirs(carpeta_procesados, exist_ok=True)
    os.makedirs(carpeta_errores, exist_ok=True)

    pdfs = [f for f in os.listdir(carpeta_pendientes) if f.lower().endswith(".pdf")]
    if not pdfs:
        print(f"[AVISO] No hay PDFs en '{carpeta_pendientes}'")
        return

    fecha_ejecucion = datetime.now().strftime("%Y-%m-%d")
    print(f"Procesando {len(pdfs)} archivo(s) para {proveedor}/{region}...\n")
    resultados = []

    for nombre in pdfs:
        ruta = os.path.join(carpeta_pendientes, nombre)
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

            # Mover PDF a procesados/ o errores/ con fecha al frente
            destino = carpeta_procesados if resultado.aprobado else carpeta_errores
            nombre_base = f"{fecha_ejecucion}_{nombre}"
            shutil.move(ruta, os.path.join(destino, nombre_base))

            # Guardar texto OCR junto al PDF
            nombre_txt = os.path.splitext(nombre_base)[0] + "_ocr.txt"
            with open(os.path.join(destino, nombre_txt), "w", encoding="utf-8") as f:
                f.write(texto)

        except Exception as ex:
            print(f"ERROR al procesar: {ex}")

    ruta_excel = actualizar_excel(resultados, carpeta_proveedor, fecha_ejecucion)
    print(f"\nReporte actualizado: {ruta_excel}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sistema de auditoría de acuses")
    parser.add_argument("--proveedor", default="EMA", help="Código del proveedor (ej: EMA)")
    parser.add_argument("--region",    default="BAN", help="Código de región (ej: BAN)")
    args = parser.parse_args()

    procesar(args.proveedor, args.region)
