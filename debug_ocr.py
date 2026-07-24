"""Script de diagnóstico: muestra el texto extraído por OCR de cada región del PDF."""
import sys
from core.pdf_processor import PDFProcessor

if len(sys.argv) < 2:
    print("Uso: python debug_ocr.py <ruta_al_pdf>")
    sys.exit(1)

ruta = sys.argv[1]
p = PDFProcessor()

regiones = {
    "HEADER   (0.00-1.00, 0.00-0.28)": (0.00, 0.00, 1.00, 0.28),
    "VISITA_1 (0.00-0.50, 0.25-0.50)": (0.00, 0.25, 0.50, 0.50),
    "VISITA_2 (0.50-1.00, 0.25-0.50)": (0.50, 0.25, 1.00, 0.50),
}

for nombre, region in regiones.items():
    print(f"\n{'='*60}")
    print(f"REGIÓN: {nombre}")
    print('='*60)
    texto = p.extraer_texto_region(ruta, region)
    print(texto if texto.strip() else "(vacío)")
