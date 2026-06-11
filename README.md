# Sistema de Auditoría de Acuses

Sistema que lee archivos PDF de acuses de visita, extrae la información relevante y verifica que cumplan con los criterios de auditoría. Genera un reporte en Excel con los resultados.

---

## Requisitos previos

Antes de usar el sistema necesitás instalar tres cosas:

### 1. Python
Verificá si ya lo tenés abriendo el `cmd` y escribiendo:
```
python --version
```
Si no lo tenés, descargarlo de: https://www.python.org/downloads/  
Durante la instalación tildar **"Add Python to PATH"**.

---

### 2. Tesseract OCR (lector de texto en imágenes)

1. Entrar a: https://github.com/UB-Mannheim/tesseract/wiki
2. Descargar el instalador `tesseract-ocr-w64-setup-x.x.x.exe` (64 bit)
3. Ejecutarlo y durante la instalación:
   - En **"Additional language data"** → tildar **Spanish**
   - Dejar la ruta por defecto: `C:\Program Files\Tesseract-OCR`

---

### 3. Poppler (lector de PDFs)

1. Entrar a: https://github.com/oschwartz10612/poppler-windows/releases
2. Descargar el archivo `Release-xx.xx.x-0.zip`
3. Descomprimirlo, renombrar la carpeta a `poppler` y moverla a `C:\`
4. Verificar que exista: `C:\poppler\Library\bin\pdftoppm.exe`

---

## Instalación del sistema

1. Descomprimír el archivo `sistemas-acuses.zip` en una carpeta
2. Abrir el `cmd` dentro de esa carpeta (click en la barra de direcciones del Explorador → escribir `cmd` → Enter)
3. Ejecutar:
```
pip install -r requirements.txt
```

---

## Configuración

Abrir el archivo `config.py` y verificar que las rutas sean correctas para tu computadora:

```python
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH  = r"C:\poppler\Library\bin"
```

Si Tesseract quedó instalado en otra ruta (por ejemplo en usuarios), buscarla con:
```
where /r C:\ tesseract.exe
```
Y reemplazarla en `config.py`.

---

## Cómo usar el sistema

### Paso 1 — Agregar los PDFs
Copiar todos los archivos PDF a auditar dentro de la carpeta `input/`.

> No importa el nombre del archivo. Podés poner mezclados bajo firma y bajo puerta, el sistema los detecta automáticamente.

### Paso 2 — Ejecutar
En el `cmd` (parado en la carpeta del proyecto):
```
python main.py
```

### Paso 3 — Ver el resultado
Abrir la carpeta `output/`. Se genera un archivo Excel con la fecha y hora del procesamiento.

---

## Qué audita el sistema

### Bajo Puerta
| Campo | Criterio |
|---|---|
| Fecha de emisión | Debe estar presente |
| Visitas | Deben ser 2, posteriores o iguales a la fecha de emisión, no caer en sábado ni domingo |
| Distribuidor | Debe estar presente |
| Características de la casa | Deben ser 3 |
| Tipo de entrega | Debe decir "Bajo Puerta" |

### Bajo Firma
| Campo | Criterio |
|---|---|
| Fecha de emisión | Debe estar presente |
| Visita | Debe ser 1, posterior o igual a la fecha de emisión, no caer en sábado ni domingo |
| Distribuidor | Debe estar presente |
| DNI | Debe estar presente |
| Nombre y apellido | Deben estar presentes en el campo Aclaración |
| Tipo de vínculo | Debe ser un vínculo directo (ver lista abajo) |
| Características de la casa | Deben ser 3 |
| Firma digitalizada | Debe estar presente |

#### Vínculos permitidos
Titular, Hijo, Hija, Esposo, Esposa, Padre, Madre, Hermano, Hermana, Cónyuge, Familiar.

> Vecino, Inquilino y cualquier otro vínculo no directo son considerados **error**.

---

## Resultado en Excel

Cada fila representa un PDF procesado. Las filas se colorean:
- 🟢 **Verde** → Aprobado (cumple todos los criterios)
- 🔴 **Rojo** → Rechazado (la columna "Errores" detalla qué falló)

---

## Agregar un nuevo proveedor

El sistema está preparado para soportar múltiples proveedores. Cada proveedor tiene su propia lógica de extracción y validación en una carpeta separada:

```
providers/
└── ema/
    └── ban/
        ├── extractor.py   ← lee los campos del PDF
        └── validator.py   ← valida las reglas de negocio
```

Para agregar un nuevo proveedor crear una nueva carpeta con la misma estructura y registrarlo en `main.py`.

---

## Problemas frecuentes

| Error | Solución |
|---|---|
| `tesseract.exe is not installed` | Verificar la ruta en `config.py` con `where /r C:\ tesseract.exe` |
| `Unable to get page count` | Verificar que Poppler esté en `C:\poppler\Library\bin` |
| `No module named 'cv2'` | Correr `pip install -r requirements.txt` de nuevo |
| No genera Excel | Verificar que la carpeta `output/` exista dentro del proyecto |
