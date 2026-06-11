import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import cv2
import numpy as np
import config


class PDFProcessor:
    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
        self._cache: dict = {}

    def _obtener_imagenes(self, ruta_pdf: str) -> list:
        if ruta_pdf not in self._cache:
            self._cache[ruta_pdf] = convert_from_path(
                ruta_pdf,
                dpi=config.PDF_DPI,
                poppler_path=config.POPPLER_PATH,
            )
        return self._cache[ruta_pdf]

    def _preprocesar(self, imagen: Image.Image) -> Image.Image:
        img_np = np.array(imagen)
        gris = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        _, binaria = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return Image.fromarray(binaria)

    def extraer_texto(self, ruta_pdf: str) -> str:
        """Extrae texto completo de todas las páginas del PDF."""
        imagenes = self._obtener_imagenes(ruta_pdf)
        texto = ""
        for imagen in imagenes:
            texto += pytesseract.image_to_string(self._preprocesar(imagen), lang=config.OCR_LANG) + "\n"
        return texto

    def extraer_texto_region(self, ruta_pdf: str, region: tuple, pagina: int = 0) -> str:
        """
        Extrae texto de una región específica de la página.
        region: (x1%, y1%, x2%, y2%) como fracción del tamaño total (0.0 a 1.0)
        """
        imagenes = self._obtener_imagenes(ruta_pdf)
        if not imagenes or pagina >= len(imagenes):
            return ""
        img_np = np.array(imagenes[pagina])
        h, w = img_np.shape[:2]
        x1, y1, x2, y2 = region
        recorte = img_np[int(y1*h):int(y2*h), int(x1*w):int(x2*w)]
        return pytesseract.image_to_string(self._preprocesar(Image.fromarray(recorte)), lang=config.OCR_LANG)

    def tiene_firma_en_region(self, ruta_pdf: str, region: tuple, pagina: int = 0) -> bool:
        """
        Detecta firma digitalizada por densidad de píxeles oscuros en una región.
        region: (x1%, y1%, x2%, y2%)
        """
        imagenes = self._obtener_imagenes(ruta_pdf)
        if not imagenes or pagina >= len(imagenes):
            return False
        img_np = np.array(imagenes[pagina])
        h, w = img_np.shape[:2]
        x1, y1, x2, y2 = region
        recorte = img_np[int(y1*h):int(y2*h), int(x1*w):int(x2*w)]
        gris = cv2.cvtColor(recorte, cv2.COLOR_RGB2GRAY)
        densidad = np.sum(gris < 100) / gris.size
        return densidad > 0.02
