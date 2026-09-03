import os
import re
import sys
import time
from datetime import datetime
import pytz
from playwright.sync_api import sync_playwright

EMAIL = os.getenv("GYM_EMAIL", "javier.pachecoe@usm.cl")
PASSWORD = os.getenv("GYM_PASSWORD")
TARGET_BLOCK = "8:15"  # Bloque 1-2 (8:15)

TZ_CHILE = pytz.timezone("America/Santiago")

def esperar_a_las_630():
    print("Sincronizando reloj con hora oficial de Chile...")
    while True:
        ahora = datetime.now(TZ_CHILE)
        if ahora.hour == 6 and ahora.minute >= 30:
            print(f"¡Son las {ahora.strftime('%H:%M:%S.%f')}! Tomando cupo...")
            break
        elif ahora.hour > 6:
            print(f"Hora actual ({ahora.strftime('%H:%M:%S')}) fuera del umbral de espera matutino.")
            break
        time.sleep(0.15)

def main():
    if not PASSWORD:
        print("Error: La variable GYM_PASSWORD no está configurada en los Secrets.")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            print("1. Accediendo a reservasgimnasiosantiago.cl...")
            page.goto("https://reservasgimnasiosantiago.cl/", wait_until="networkidle", timeout=30000)

            print("2. Completando credenciales...")
            page.fill("input[type='email']", EMAIL)
            page.fill("input[type='password']", PASSWORD)
            
            # Para asegurar el envío del formulario:
            # Opción 1: Presionar Enter en el input de password
            page.press("input[type='password']", "Enter")
            
            # Opción 2: Buscar el botón de submit o el último botón con texto 'Iniciar sesión'
            time.sleep(1)
            btn_submit = page.locator("button[type='submit'], form button").filter(has_text=re.compile(r"iniciar", re.I))
            if btn_submit.count() > 0:
                btn_submit.last.click(force=True)

            print("Esperando respuesta tras inicio de sesión...")
            time.sleep(3)

            # 3. Cerrar popup de advertencia
            try:
                print("Verificando popup de advertencia...")
                modal_btn = page.locator("button, [role='button'], .swal2-confirm, div").filter(has_text=re.compile(r"entendido", re.I))
                if modal_btn.first.is_visible(timeout=5000):
                    modal_btn.first.click(force=True)
                    print("Popup cerrado exitosamente.")
                    time.sleep(1)
            except Exception:
                print("No se detectó popup activo.")

            # 4. Seleccionar sede San Joaquín (con o sin tilde)
            print("Seleccionando sede San Joaquín...")
            sede_locator = page.locator("button, a, div, span").filter(has_text=re.compile(r"san joaqu[ií]n", re.I))
            sede_locator.first.wait_for(state="visible", timeout=12000)
            sede_locator.first.click(force=True)
            print("Sede San Joaquín seleccionada.")
            time.sleep(1)

            # 5. Espera activa hasta las 06:30:00 AM
            esperar_a_las_630()

            # 6. Forzar actualización de la sede para habilitar botones
            try:
                sede_locator.first.click(force=True)
                time.sleep(0.2)
            except Exception:
                pass

            # 7. Clic sobre el bloque objetivo 8:15
            print(f"Buscando bloque horario {TARGET_BLOCK}...")
            bloque = page.locator("button, [role='button'], div, span").filter(has_text=re.compile(TARGET_BLOCK))
            bloque.first.wait_for(state="visible", timeout=5000)
            bloque.first.click(force=True)
            print("¡Clic en el bloque realizado!")

            time.sleep(2)
            page.screenshot(path="comprobante_reserva.png")
            print("Captura final guardada en comprobante_reserva.png")

        except Exception as e:
            print(f"\n[ALERTA] Ocurrió un error en el flujo: {e}")
            page.screenshot(path="error_pantalla.png")
            print("Captura del estado actual guardada en error_pantalla.png")
            raise e

        finally:
            browser.close()

if __name__ == "__main__":
    main()
