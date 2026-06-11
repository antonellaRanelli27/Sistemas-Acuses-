import os

import sys

# Rutas de Tesseract y Poppler
if sys.platform == "win32":
    TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    POPPLER_PATH = r"C:\poppler\Library\bin"
else:
    TESSERACT_CMD = "/usr/bin/tesseract"
    POPPLER_PATH = None  # en Linux/Mac está en el PATH

# Carpetas de entrada y salida
INPUT_FOLDER = os.path.join(os.path.dirname(__file__), "input")
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), "output")

# Idioma OCR
OCR_LANG = "spa"

# DPI para conversión de PDF a imagen (mayor = más preciso, más lento)
PDF_DPI = 300
