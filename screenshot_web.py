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
"""

import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

# ─────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN ESTÁTICA (se puede sobreescribir con los prompts)
# ─────────────────────────────────────────────────────────────────

# Carpeta donde se guardarán los screenshots
OUTPUT_DIR = "screenshots"

# Esperar N segundos después de cargar cada página (para animaciones/JS)
WAIT_AFTER_LOAD = 1.5

# Máxima profundidad de crawl
MAX_DEPTH = 3

# Tiempo máximo de espera por página (ms)
PAGE_TIMEOUT = 30_000

# Patrones de URLs a EXCLUIR del crawl automático (regex)
EXCLUDE_PATTERNS = [
    r"\.(pdf|zip|png|jpg|jpeg|gif|svg|ico|webp|mp4|mp3|woff|woff2|ttf|eot)$",
    r"^mailto:",
    r"^tel:",
    r"^javascript:",
    r"#",
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

def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║          🖥️   SCREENSHOT MULTI-SHOT  📱                      ║
║     Full-page · Desktop · Tablet · Mobile                    ║
╚══════════════════════════════════════════════════════════════╝
""")


def ask(prompt: str, default: str = "") -> str:
    """Pregunta al usuario y devuelve la respuesta. Si hay default lo muestra."""
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"  {prompt}{suffix}: ").strip()
        return value if value else default
    except (KeyboardInterrupt, EOFError):
        print("\n\n⛔ Cancelado por el usuario.")
        sys.exit(0)


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "[S/n]" if default else "[s/N]"
    try:
        value = input(f"  {prompt} {suffix}: ").strip().lower()
        if not value:
            return default
        return value in ("s", "si", "sí", "y", "yes")
    except (KeyboardInterrupt, EOFError):
        print("\n\n⛔ Cancelado por el usuario.")
        sys.exit(0)


def normalize_url(url: str, base: str):
    url = url.strip()
    if not url:
        return None
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return None
    full = urljoin(base, url)
    parsed = urlparse(full)
    base_parsed = urlparse(base)
    if parsed.netloc != base_parsed.netloc:
        return None
    full = parsed._replace(fragment="").geturl()
    return full


def url_to_filename(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if not path:
        path = "index"
    safe = re.sub(r"[^\w\-]", "_", path)
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe or "index"


# ─────────────────────────────────────────────────────────────────
#  PROMPTS INTERACTIVOS
# ─────────────────────────────────────────────────────────────────

def collect_params() -> dict:
    """Pide al usuario todos los parámetros antes de arrancar."""

    print_banner()
    print("─" * 64)
    print("  Configura la captura respondiendo las siguientes preguntas.")
    print("  Pulsa ENTER para aceptar el valor por defecto entre [ ].")
    print("─" * 64 + "\n")

    # ── URL base ──────────────────────────────────────────────────
    while True:
        base_url = ask("🌐 URL base de tu web (ej: https://midominio.com)")
        if base_url:
            if not base_url.startswith(("http://", "https://")):
                base_url = "https://" + base_url
            print(f"     ✅ URL base: {base_url}\n")
            break
        print("     ⚠️  La URL base es obligatoria.\n")

    # ── URLs específicas ──────────────────────────────────────────
    print("  📋 URLs específicas a capturar (rutas relativas o absolutas).")
    print("     Escribe una por línea. Deja vacío y pulsa ENTER para terminar.\n")

    manual_urls = []
    idx = 1
    while True:
        url = ask(f"  URL específica #{idx} (ENTER para terminar)", "")
        if not url:
            break
        # Normalizar: si es ruta relativa la dejamos como /ruta
        if not url.startswith(("http://", "https://")):
            url = "/" + url.lstrip("/")
        manual_urls.append(url)
        print(f"     ✅ Añadida: {url}")
        idx += 1

    if not manual_urls:
        print("     ℹ️  No se añadieron URLs específicas.\n")
    else:
        print(f"\n     Total URLs específicas: {len(manual_urls)}\n")

    # ── Auto-crawl ────────────────────────────────────────────────
    do_crawl = ask_yes_no("🔍 ¿Activar auto-crawl para descubrir todas las URLs internas?", default=True)

    depth = MAX_DEPTH
    if do_crawl:
        depth_str = ask("   Profundidad máxima de crawl", str(MAX_DEPTH))
        try:
            depth = int(depth_str)
        except ValueError:
            depth = MAX_DEPTH
        print(f"     ✅ Profundidad: {depth}\n")

    # ── Dispositivos ──────────────────────────────────────────────
    print("\n  📱 Dispositivos a capturar:")
    print("     1) Desktop  (1440×900)")
    print("     2) Tablet   (768×1024)")
    print("     3) Mobile   (390×844)")
    print("     Puedes elegir varios separados por coma (ej: 1,3)")

    device_map = {"1": "desktop", "2": "tablet", "3": "mobile"}
    while True:
        sel = ask("  Selección", "1,2,3")
        selected_devices = []
        for s in sel.split(","):
            s = s.strip()
            if s in device_map:
                selected_devices.append(device_map[s])
        if selected_devices:
            print(f"     ✅ Dispositivos: {', '.join(selected_devices)}\n")
            break
        print("     ⚠️  Selección no válida. Usa números del 1 al 3.\n")

    # ── Carpeta de salida ─────────────────────────────────────────
    output_dir = ask("📁 Carpeta de salida", OUTPUT_DIR)
    print(f"     ✅ Carpeta: {output_dir}\n")

    # ── Resumen ───────────────────────────────────────────────────
    print("\n" + "─" * 64)
    print("  📝 RESUMEN DE CONFIGURACIÓN")
    print("─" * 64)
    print(f"  URL base         : {base_url}")
    print(f"  URLs específicas : {manual_urls if manual_urls else '(ninguna)'}")
    print(f"  Auto-crawl       : {'Sí (profundidad ' + str(depth) + ')' if do_crawl else 'No'}")
    print(f"  Dispositivos     : {', '.join(selected_devices)}")
    print(f"  Carpeta salida   : {output_dir}")
    print("─" * 64 + "\n")

    ok = ask_yes_no("¿Todo correcto? ¿Arrancamos?", default=True)
    if not ok:
        print("\n  🔄 Reiniciando configuración...\n")
        return collect_params()

    return {
        "base_url": base_url.rstrip("/"),
        "manual_urls": manual_urls,
        "do_crawl": do_crawl,
        "depth": depth,
        "devices": selected_devices,
        "output_dir": Path(output_dir),
    }


# ─────────────────────────────────────────────────────────────────
#  CRAWLER
# ─────────────────────────────────────────────────────────────────

def crawl_urls(base_url: str, max_depth: int, page) -> list:
    visited = set()
    to_visit = [(base_url, 0)]
    found = []

    print(f"\n🔍 Iniciando crawl desde: {base_url}")

    while to_visit:
        url, depth = to_visit.pop(0)

        if url in visited:
            continue
        if depth > max_depth:
            continue

        visited.add(url)
        found.append(url)
        print(f"   [depth={depth}] {url}")

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            time.sleep(0.3)

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
    # Verificar Playwright antes de preguntar nada
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright no está instalado.")
        print("   Ejecuta:  pip install playwright && playwright install chromium")
        sys.exit(1)

    # ── Recoger parámetros interactivamente ───────────────────────
    cfg = collect_params()

    base_url    = cfg["base_url"]
    manual_urls = cfg["manual_urls"]
    do_crawl    = cfg["do_crawl"]
    depth       = cfg["depth"]
    devices     = cfg["devices"]
    output_dir  = cfg["output_dir"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ── FASE 1: Construir lista de URLs ───────────────────────
        all_urls = []

        # Añadir URLs manuales (convirtiéndolas a absolutas)
        for rel in manual_urls:
            full = urljoin(base_url + "/", rel.lstrip("/"))
            if full not in all_urls:
                all_urls.append(full)

        # Asegurar que la raíz siempre está
        root = base_url + "/"
        if root not in all_urls:
            all_urls.insert(0, root)

        if do_crawl:
            crawl_ctx = browser.new_context(viewport={"width": 1280, "height": 800})
            crawl_page = crawl_ctx.new_page()
            crawled = crawl_urls(base_url, depth, crawl_page)
            crawl_page.close()
            crawl_ctx.close()

            for u in crawled:
                if u not in all_urls:
                    all_urls.append(u)

        print(f"\n📋 Total de URLs a capturar: {len(all_urls)}")
        for u in all_urls:
            print(f"   • {u}")

        # ── FASE 2: Screenshots ───────────────────────────────────
        total_ok   = 0
        total_fail = 0
        start_time = time.time()

        for device_name in devices:
            device_cfg = DEVICES[device_name]
            print(f"\n{'═' * 62}")
            print(f"  📱 Dispositivo: {device_name.upper()}  "
                  f"({device_cfg['viewport']['width']}×"
                  f"{device_cfg['viewport']['height']})")
            print(f"{'═' * 62}")

            ctx = browser.new_context(
                viewport=device_cfg["viewport"],
                device_scale_factor=device_cfg["device_scale_factor"],
                user_agent=device_cfg["user_agent"],
            )
            page = ctx.new_page()

            for i, url in enumerate(all_urls, 1):
                filename = url_to_filename(url)
                filepath = output_dir / device_name / f"{filename}.png"

                print(f"  [{i:02d}/{len(all_urls):02d}] {url}")
                print(f"         → {filepath}")

                ok = take_screenshot(page, url, filepath)
                if ok:
                    total_ok += 1
                    print("         ✅ OK")
                else:
                    total_fail += 1

            page.close()
            ctx.close()

        browser.close()

        # ── Resumen final ─────────────────────────────────────────
        elapsed = time.time() - start_time
        print(f"\n{'═' * 62}")
        print(f"  🎉 COMPLETADO en {elapsed:.1f}s")
        print(f"  ✅ Éxitos  : {total_ok}")
        print(f"  ❌ Errores : {total_fail}")
        print(f"  📁 Carpeta : {output_dir.resolve()}")
        print(f"{'═' * 62}\n")

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
