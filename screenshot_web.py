#!/usr/bin/env python3
"""
screenshot_web.py
=================
Captura screenshots full-page de toda una web en resoluciones Desktop,
Tablet y Móvil. Combina una lista manual de URLs con auto-crawling de
todos los enlaces internos encontrados.

Requisitos:
    pip install playwright
    playwright install chromium

Uso:
    python screenshot_web.py

    # Con URL distinta a la configurada:
    python screenshot_web.py --url https://midominio.com

    # Solo URLs manuales, sin crawling automático:
    python screenshot_web.py --no-crawl

    # Limitar profundidad del crawl:
    python screenshot_web.py --depth 2

    # Cambiar carpeta de salida:
    python screenshot_web.py --output mis_screenshots
"""

import argparse
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

# ─────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN  ← edita esta sección según tu proyecto
# ─────────────────────────────────────────────────────────────────

BASE_URL = "https://example.com"          # ← cambia por tu URL base

# URLs que SIEMPRE se capturarán (además de las descubiertas por crawl)
MANUAL_URLS = [
    "/",
    # "/about",
    # "/contact",
    # "/blog",
    # "/productos",
]

# Carpeta donde se guardarán los screenshots
OUTPUT_DIR = "screenshots"

# Esperar N segundos después de cargar cada página (para animaciones/JS)
WAIT_AFTER_LOAD = 1.5

# Máxima profundidad de crawl (None = sin límite)
MAX_DEPTH = 3

# Tiempo máximo de espera por página (ms)
PAGE_TIMEOUT = 30_000

# Patrones de URLs a EXCLUIR del crawl automático (regex)
EXCLUDE_PATTERNS = [
    r"\.(pdf|zip|png|jpg|jpeg|gif|svg|ico|webp|mp4|mp3|woff|woff2|ttf|eot)$",
    r"^mailto:",
    r"^tel:",
    r"^javascript:",
    r"#",                     # anclas dentro de la misma página
    r"/logout",
    r"/admin",
]

# ─────────────────────────────────────────────────────────────────
#  RESOLUCIONES
# ─────────────────────────────────────────────────────────────────

DEVICES = {
    "desktop": {
        "viewport": {"width": 1440, "height": 900},
        "device_scale_factor": 1,
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    },
    "tablet": {
        "viewport": {"width": 768, "height": 1024},
        "device_scale_factor": 2,
        "user_agent": (
            "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.0 Mobile/15E148 Safari/604.1"
        ),
    },
    "mobile": {
        "viewport": {"width": 390, "height": 844},
        "device_scale_factor": 3,
        "user_agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.0 Mobile/15E148 Safari/604.1"
        ),
    },
}


# ─────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────

def normalize_url(url: str, base: str) -> str | None:
    """Convierte una URL relativa en absoluta y valida que sea interna."""
    url = url.strip()
    if not url:
        return None

    # Filtrar por patrones excluidos
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return None

    full = urljoin(base, url)
    parsed = urlparse(full)
    base_parsed = urlparse(base)

    # Solo URLs del mismo dominio
    if parsed.netloc != base_parsed.netloc:
        return None

    # Limpiar fragmento
    full = parsed._replace(fragment="").geturl()
    return full


def url_to_filename(url: str, base: str) -> str:
    """Convierte una URL en un nombre de archivo seguro."""
    path = urlparse(url).path.strip("/")
    if not path:
        path = "index"
    # Reemplazar separadores por guiones
    safe = re.sub(r"[^\w\-]", "_", path)
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe or "index"


def should_exclude(url: str) -> bool:
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


# ─────────────────────────────────────────────────────────────────
#  CRAWLER
# ─────────────────────────────────────────────────────────────────

def crawl_urls(base_url: str, max_depth: int | None, page) -> list[str]:
    """
    Recorre la web a partir de base_url y devuelve todas las URLs internas
    únicas encontradas.
    """
    visited: set[str] = set()
    to_visit: list[tuple[str, int]] = [(base_url, 0)]
    found: list[str] = []

    print(f"\n🔍 Iniciando crawl desde: {base_url}")

    while to_visit:
        url, depth = to_visit.pop(0)

        if url in visited:
            continue
        if max_depth is not None and depth > max_depth:
            continue

        visited.add(url)
        found.append(url)
        print(f"   [depth={depth}] {url}")

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            time.sleep(0.3)

            # Extraer todos los hrefs de la página
            links = page.eval_on_selector_all(
                "a[href]",
                "elements => elements.map(el => el.getAttribute('href'))"
            )

            for link in links:
                normalized = normalize_url(link, base_url)
                if normalized and normalized not in visited:
                    to_visit.append((normalized, depth + 1))

        except Exception as e:
            print(f"   ⚠️  Error crawling {url}: {e}")

    print(f"\n✅ Crawl completado: {len(found)} URLs encontradas\n")
    return found


# ─────────────────────────────────────────────────────────────────
#  SCREENSHOT
# ─────────────────────────────────────────────────────────────────

def take_screenshot(page, url: str, filepath: Path) -> bool:
    """Navega a la URL y toma un screenshot full-page."""
    try:
        page.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT)
        time.sleep(WAIT_AFTER_LOAD)

        # Scroll suave para activar lazy-loading
        page.evaluate("""
            async () => {
                await new Promise(resolve => {
                    let totalHeight = 0;
                    const distance = 300;
                    const timer = setInterval(() => {
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        if (totalHeight >= document.body.scrollHeight) {
                            clearInterval(timer);
                            window.scrollTo(0, 0);
                            resolve();
                        }
                    }, 80);
                });
            }
        """)
        time.sleep(0.5)

        filepath.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(filepath), full_page=True)
        return True

    except Exception as e:
        print(f"      ❌ Error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Screenshots full-page de una web en múltiples resoluciones"
    )
    parser.add_argument(
        "--url",
        default=BASE_URL,
        help=f"URL base de la web (default: {BASE_URL})"
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_DIR,
        help=f"Carpeta de salida (default: {OUTPUT_DIR})"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=MAX_DEPTH,
        help=f"Profundidad máxima de crawl (default: {MAX_DEPTH})"
    )
    parser.add_argument(
        "--no-crawl",
        action="store_true",
        help="Desactiva el auto-crawl; solo usa MANUAL_URLS"
    )
    parser.add_argument(
        "--devices",
        nargs="+",
        choices=list(DEVICES.keys()),
        default=list(DEVICES.keys()),
        help="Dispositivos a capturar (default: todos)"
    )
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    output_dir = Path(args.output)

    # ── Importar Playwright ────────────────────────────────────────
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright no está instalado.")
        print("   Ejecuta:  pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ── FASE 1: Crawl de URLs ──────────────────────────────────
        all_urls: list[str] = []

        # Añadir URLs manuales
        for rel in MANUAL_URLS:
            full = urljoin(base_url + "/", rel.lstrip("/"))
            if full not in all_urls:
                all_urls.append(full)

        if not args.no_crawl:
            # Usamos un contexto ligero solo para crawlear
            crawl_ctx = browser.new_context(
                viewport={"width": 1280, "height": 800}
            )
            crawl_page = crawl_ctx.new_page()
            crawled = crawl_urls(base_url, args.depth, crawl_page)
            crawl_page.close()
            crawl_ctx.close()

            for u in crawled:
                if u not in all_urls:
                    all_urls.append(u)

        print(f"📋 Total de URLs a capturar: {len(all_urls)}")
        for u in all_urls:
            print(f"   • {u}")

        # ── FASE 2: Screenshots ────────────────────────────────────
        total_ok = 0
        total_fail = 0
        start_time = time.time()

        for device_name in args.devices:
            device_cfg = DEVICES[device_name]
            print(f"\n{'═' * 60}")
            print(f"  📱 Dispositivo: {device_name.upper()}  "
                  f"({device_cfg['viewport']['width']}×"
                  f"{device_cfg['viewport']['height']})")
            print(f"{'═' * 60}")

            ctx = browser.new_context(
                viewport=device_cfg["viewport"],
                device_scale_factor=device_cfg["device_scale_factor"],
                user_agent=device_cfg["user_agent"],
            )
            page = ctx.new_page()

            for i, url in enumerate(all_urls, 1):
                filename = url_to_filename(url, base_url)
                filepath = output_dir / device_name / f"{filename}.png"

                print(f"  [{i:02d}/{len(all_urls):02d}] {url}")
                print(f"         → {filepath}")

                ok = take_screenshot(page, url, filepath)
                if ok:
                    total_ok += 1
                    print(f"         ✅ OK")
                else:
                    total_fail += 1

            page.close()
            ctx.close()

        browser.close()

        # ── Resumen final ──────────────────────────────────────────
        elapsed = time.time() - start_time
        print(f"\n{'═' * 60}")
        print(f"  🎉 COMPLETADO en {elapsed:.1f}s")
        print(f"  ✅ Éxitos  : {total_ok}")
        print(f"  ❌ Errores : {total_fail}")
        print(f"  📁 Carpeta : {output_dir.resolve()}")
        print(f"{'═' * 60}\n")

        # Mostrar árbol de archivos generados
        if output_dir.exists():
            print("📂 Archivos generados:")
            for device_dir in sorted(output_dir.iterdir()):
                if device_dir.is_dir():
                    files = sorted(device_dir.glob("*.png"))
                    print(f"  {device_dir.name}/  ({len(files)} screenshots)")
                    for f in files:
                        size_kb = f.stat().st_size / 1024
                        print(f"    • {f.name}  ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
