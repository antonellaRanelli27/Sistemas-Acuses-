import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import cv2
import numpy as np
import fitz  # pymupdf
import config


class PDFProcessor:
    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
        self._cache: dict = {}
        self._fitz_cache: dict = {}

    def _obtener_imagenes(self, ruta_pdf: str) -> list:
        if ruta_pdf not in self._cache:
            self._cache[ruta_pdf] = convert_from_path(
                ruta_pdf,
                dpi=config.PDF_DPI,
                poppler_path=config.POPPLER_PATH,
            )
        return self._cache[ruta_pdf]

    def _obtener_doc_fitz(self, ruta_pdf: str):
        if ruta_pdf not in self._fitz_cache:
            self._fitz_cache[ruta_pdf] = fitz.open(ruta_pdf)
        return self._fitz_cache[ruta_pdf]

    def _preprocesar(self, imagen: Image.Image) -> Image.Image:
        img_np = np.array(imagen)
        gris = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        _, binaria = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return Image.fromarray(binaria)

    def _extraer_texto_fitz(self, ruta_pdf: str) -> str:
        """Extrae texto digital embebido con pymupdf (sin OCR)."""
        try:
            doc = self._obtener_doc_fitz(ruta_pdf)
            return "\n".join(page.get_text() for page in doc)
        except Exception:
            return ""

    def _extraer_texto_region_fitz(self, ruta_pdf: str, region: tuple, pagina: int = 0) -> str:
        """Extrae texto digital de una región usando pymupdf."""
        try:
            doc = self._obtener_doc_fitz(ruta_pdf)
            if pagina >= len(doc):
                return ""
            page = doc[pagina]
            r = page.rect
            x1, y1, x2, y2 = region
            clip = fitz.Rect(r.x0 + x1 * r.width, r.y0 + y1 * r.height,
                             r.x0 + x2 * r.width, r.y0 + y2 * r.height)
            return page.get_text(clip=clip)
        except Exception:
            return ""

    def extraer_texto(self, ruta_pdf: str) -> str:
        """Extrae texto completo: intenta pymupdf primero, OCR como fallback."""
        texto = self._extraer_texto_fitz(ruta_pdf)
        if len(texto.strip()) > 50:
            return texto
        try:
            imagenes = self._obtener_imagenes(ruta_pdf)
        except Exception:
            return texto
        ocr = ""
        for imagen in imagenes:
            ocr += pytesseract.image_to_string(self._preprocesar(imagen), lang=config.OCR_LANG) + "\n"
        return ocr

    def extraer_texto_region(self, ruta_pdf: str, region: tuple, pagina: int = 0) -> str:
        """
        Extrae texto de una región: intenta pymupdf primero, OCR como fallback.
        region: (x1%, y1%, x2%, y2%) como fracción del tamaño total (0.0 a 1.0)
        """
        texto = self._extraer_texto_region_fitz(ruta_pdf, region, pagina)
        if len(texto.strip()) > 5:
            return texto
        try:
            imagenes = self._obtener_imagenes(ruta_pdf)
        except Exception:
            return texto
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
