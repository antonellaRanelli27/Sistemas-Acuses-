import os

# Rutas de Tesseract y Poppler en Windows
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\poppler\Library\bin"

# Carpetas de entrada y salida
INPUT_FOLDER = os.path.join(os.path.dirname(__file__), "input")
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), "output")

# Idioma OCR
OCR_LANG = "spa"

# DPI para conversión de PDF a imagen (mayor = más preciso, más lento)
PDF_DPI = 300
