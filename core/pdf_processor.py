import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import cv2
import numpy as np
import config


class PDFProcessor:
    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD

    def _preprocesar_imagen(self, imagen: Image.Image) -> Image.Image:
        img_np = np.array(imagen)
        gris = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        _, binaria = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return Image.fromarray(binaria)

    def extraer_texto(self, ruta_pdf: str) -> str:
        imagenes = convert_from_path(
            ruta_pdf,
            dpi=config.PDF_DPI,
            poppler_path=config.POPPLER_PATH
        )
        texto_completo = ""
        for imagen in imagenes:
            imagen_procesada = self._preprocesar_imagen(imagen)
            texto = pytesseract.image_to_string(imagen_procesada, lang=config.OCR_LANG)
            texto_completo += texto + "\n"
        return texto_completo

    def tiene_firma_en_region(self, ruta_pdf: str, region: tuple) -> bool:
        """
        Detecta si hay una firma dibujada en una región específica de la imagen.
        region: (x, y, ancho, alto) en porcentaje del tamaño total (0.0 a 1.0)
        """
        imagenes = convert_from_path(
            ruta_pdf,
            dpi=config.PDF_DPI,
            poppler_path=config.POPPLER_PATH
        )
        if not imagenes:
            return False

        img_np = np.array(imagenes[0])
        h, w = img_np.shape[:2]
        x_pct, y_pct, w_pct, h_pct = region
        x1 = int(x_pct * w)
        y1 = int(y_pct * h)
        x2 = int((x_pct + w_pct) * w)
        y2 = int((y_pct + h_pct) * h)

        recorte = img_np[y1:y2, x1:x2]
        gris = cv2.cvtColor(recorte, cv2.COLOR_RGB2GRAY)
        pixeles_oscuros = np.sum(gris < 100)
        total_pixeles = gris.size
        densidad = pixeles_oscuros / total_pixeles

        # Si más del 2% de los píxeles son oscuros, se considera que hay firma
        return densidad > 0.02
