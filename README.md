# 📸 Screen Multi-Shot

Herramienta para capturar **screenshots full-page** de toda una web de forma automática, en tres resoluciones distintas: **Desktop**, **Tablet** y **Móvil**.

Combina una lista de URLs que tú eliges con un **crawler automático** que descubre todos los enlaces internos de la web.

---

## ✨ Características

- 🖥️ **3 resoluciones** — Desktop (1440px), Tablet (768px) y Mobile (390px)
- 📄 **Full-page** — captura toda la página con scroll, no solo el viewport
- 🦥 **Lazy-loading** — hace scroll progresivo antes de capturar para cargar imágenes diferidas
- 🔍 **Auto-crawl** — descubre automáticamente todas las URLs internas de la web
- 📋 **URLs manuales** — añade rutas específicas que siempre quieres capturar
- 💬 **Configuración interactiva** — te pregunta todo antes de arrancar, sin tocar código
- 📁 **Salida organizada** — carpetas separadas por dispositivo

---

## 📦 Requisitos

Python 3.10 o superior y el navegador Chromium de Playwright.

```bash
pip install -r requirements_screenshots.txt
playwright install chromium
```

---

## 🚀 Uso

Simplemente ejecuta el script y responde las preguntas:

```bash
python screenshot_web.py
```

El script te irá preguntando paso a paso:

```
╔══════════════════════════════════════════════════════════════╗
║          🖥️   SCREENSHOT MULTI-SHOT  📱                      ║
║     Full-page · Desktop · Tablet · Mobile                    ║
╚══════════════════════════════════════════════════════════════╝

  🌐 URL base de tu web (ej: https://midominio.com): https://midominio.com

  📋 URL específica #1 (ENTER para terminar): /about
  📋 URL específica #2 (ENTER para terminar): /contacto
  📋 URL específica #3 (ENTER para terminar):   ← ENTER vacío para terminar

  🔍 ¿Activar auto-crawl para descubrir todas las URLs internas? [S/n]: s
     Profundidad máxima de crawl [3]: 2

  📱 Dispositivos a capturar:
     1) Desktop  (1440×900)
     2) Tablet   (768×1024)
     3) Mobile   (390×844)
  Selección [1,2,3]: 1,3

  📁 Carpeta de salida [screenshots]:

  📝 RESUMEN DE CONFIGURACIÓN
  ────────────────────────────────────────────────────────────────
  URL base         : https://midominio.com
  URLs específicas : ['/about', '/contacto']
  Auto-crawl       : Sí (profundidad 2)
  Dispositivos     : desktop, mobile
  Carpeta salida   : screenshots
  ────────────────────────────────────────────────────────────────

  ¿Todo correcto? ¿Arrancamos? [S/n]: s
```

---

## 📂 Estructura de salida

```
screenshots/
├── desktop/               ← 1440×900 px
│   ├── index.png
│   ├── about.png
│   └── contacto.png
├── tablet/                ← 768×1024 px (retina ×2)
│   ├── index.png
│   └── ...
└── mobile/                ← 390×844 px (retina ×3)
    ├── index.png
    └── ...
```

Cada archivo PNG tiene el nombre de la ruta de la URL. La raíz `/` se guarda como `index.png`.

---

## ❓ Preguntas del asistente — detalle

### 🌐 URL base
La URL raíz de tu web. Puede ser un dominio real o localhost.

| Ejemplo | Válido |
|---|---|
| `https://midominio.com` | ✅ |
| `http://localhost:3000` | ✅ |
| `midominio.com` | ✅ (añade `https://` automáticamente) |

---

### 📋 URLs específicas
Rutas que **siempre** se capturarán, independientemente del crawl. Escríbelas de una en una. Deja la línea vacía y pulsa **ENTER** para terminar.

Puedes usar rutas relativas o URLs completas:

```
/about
/blog/primer-post
https://midominio.com/contacto
```

> La raíz `/` siempre se incluye automáticamente aunque no la escribas.

---

### 🔍 Auto-crawl
Si lo activas, el script visitará la web empezando por la URL base y seguirá todos los enlaces internos que encuentre, descubriendo páginas automáticamente.

**Profundidad de crawl:**

| Valor | Qué visita |
|---|---|
| `1` | Solo la raíz y sus enlaces directos |
| `2` | Raíz → sus enlaces → los enlaces de esos |
| `3` | Tres niveles de profundidad (recomendado) |
| `0` | Solo la URL base |

Las siguientes URLs se **excluyen** siempre del crawl para evitar problemas:
- Archivos: `.pdf`, `.zip`, `.png`, `.jpg`, `.gif`, `.mp4`, etc.
- `mailto:`, `tel:`, `javascript:`
- Anclas (`#`)
- `/logout`, `/admin`

---

### 📱 Dispositivos
Elige uno o varios separados por coma:

| Opción | Resolución | User-Agent |
|---|---|---|
| `1` Desktop | 1440×900 | Chrome en Windows |
| `2` Tablet | 768×1024 | Safari en iPad |
| `3` Mobile | 390×844 | Safari en iPhone |

Ejemplo para capturar solo desktop y móvil: `1,3`

---

### 📁 Carpeta de salida
Directorio donde se guardarán los screenshots. Se crea automáticamente si no existe. Por defecto: `screenshots/`.

---

## ⚙️ Configuración avanzada

Si quieres cambiar valores por defecto sin responder las preguntas cada vez, edita la sección `CONFIGURACIÓN ESTÁTICA` al inicio del archivo `screenshot_web.py`:

```python
OUTPUT_DIR     = "screenshots"   # Carpeta por defecto
WAIT_AFTER_LOAD = 1.5            # Segundos de espera post-carga
MAX_DEPTH      = 3               # Profundidad de crawl por defecto
PAGE_TIMEOUT   = 30_000          # Tiempo máximo por página (ms)
```

Para añadir o quitar patrones de URLs excluidas del crawl, modifica `EXCLUDE_PATTERNS`:

```python
EXCLUDE_PATTERNS = [
    r"\.(pdf|zip|png|...)$",
    r"/mi-ruta-privada",     # ← añade tus exclusiones aquí
]
```

---

## 🗂️ Cómo funciona internamente

```
python screenshot_web.py
        │
        ▼
┌─────────────────────┐
│  1. Preguntas       │  Recoge URL base, rutas manuales,
│     interactivas    │  dispositivos, profundidad, etc.
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  2. Crawl           │  Visita la web con Playwright y
│     automático      │  extrae todos los <a href> internos
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  3. Deduplicación   │  Une URLs manuales + crawleadas,
│     de URLs         │  elimina duplicados
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐   Para cada URL:
│  4. Screenshots     │   · goto(url, networkidle)
│     full-page       │   · scroll suave (lazy-load)
│     × dispositivo   │   · screenshot(full_page=True)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  5. Resumen final   │  Muestra éxitos/errores y árbol
│                     │  de archivos con tamaño en KB
└─────────────────────┘
```

---

## 📋 Requisitos del sistema

| Requisito | Versión mínima |
|---|---|
| Python | 3.10+ |
| playwright | 1.44+ |
| Chromium | instalado vía `playwright install chromium` |

---

## 📄 Licencia

MIT
