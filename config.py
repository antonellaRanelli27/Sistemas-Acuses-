import os
import sys

# Rutas de Tesseract y Poppler
if sys.platform == "win32":
    TESSERACT_CMD = r"C:\Tesseract-OCR\tesseract.exe"
    POPPLER_PATH = r"C:\poppler\Library\bin"
else:
    TESSERACT_CMD = "/usr/bin/tesseract"
    POPPLER_PATH = None  # en Linux/Mac está en el PATH

# Carpeta base donde viven las carpetas de cada proveedor
BASE_DIR = os.path.dirname(__file__)

# Idioma OCR
OCR_LANG = "spa"

# DPI para conversión de PDF a imagen (mayor = más preciso, más lento)
PDF_DPI = 300
