import os
import re
import sys
import time
from datetime import datetime
import pytz
from playwright.sync_api import sync_playwright

EMAIL = os.getenv("GYM_EMAIL", "javier.pachecoe@usm.cl")
PASSWORD = os.getenv("GYM_PASSWORD")
TARGET_BLOCK = "08:15"

TZ_CHILE = pytz.timezone("America/Santiago")

def esperar_a_las_630():
    print("Sincronizando reloj con hora oficial de Chile...")
    while True:
        ahora = datetime.now(TZ_CHILE)
        if ahora.hour == 6 and ahora.minute >= 30:
            print(f"¡Son las {ahora.strftime('%H:%M:%S.%f')}! Iniciando recarga y reserva inmediata...")
            break
        elif ahora.hour > 6:
            print(f"Hora actual ({ahora.strftime('%H:%M:%S')}) fuera del umbral de espera matutino.")
            break
        time.sleep(0.1)  # Comprobación de alta frecuencia cada 100 ms

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
            print("1. Accediendo a reservasgimnasiosantiago.cl e iniciando sesión...")
            page.goto("https://reservasgimnasiosantiago.cl/", wait_until="networkidle", timeout=30000)

            # Iniciar sesión una sola vez
            page.fill("input[type='email']", EMAIL)
            page.fill("input[type='password']", PASSWORD)
            page.press("input[type='password']", "Enter")
            time.sleep(1)

            btn_submit = page.locator("button[type='submit'], form button").filter(has_text=re.compile(r"iniciar", re.I))
            if btn_submit.count() > 0:
                btn_submit.last.click(force=True)

            # Cerrar el popup ENTENDIDO único del login
            print("Cerrando modal inicial...")
            btn_entendido = page.locator("button").filter(has_text=re.compile(r"^ENTENDIDO$", re.I))
            if btn_entendido.count() == 0:
                btn_entendido = page.get_by_text("ENTENDIDO", exact=True)
            
            btn_entendido.first.wait_for(state="visible", timeout=12000)
            btn_entendido.first.click()
            btn_entendido.first.wait_for(state="hidden", timeout=5000)
            print("Sesión lista y modal cerrado.")

            # 2. Espera de alta precisión hasta las 06:30:00 AM
            esperar_a_las_630()

            # 3. Recarga ultra rápida a las 06:30:00 (mantiene la sesión, sin popups)
            print("Recargando página a toda velocidad...")
            page.reload(wait_until="domcontentloaded")

            # 4. Ir directo a San Joaquín
            print("Seleccionando sede San Joaquín...")
            tab_sj = page.locator("button, a, div, span").filter(has_text=re.compile(r"^San Joaqu[ií]n", re.I)).first
            tab_sj.wait_for(state="visible", timeout=8000)
            tab_sj.click(force=True)

            # 5. Localizar Bloque 1-2 (08:15) y ejecutar toma segura
            print("Localizando Bloque 1-2 (08:15)...")
            card_bloque = page.locator("div").filter(has_text="08:15").filter(has_text="Bloque 1-2").last
            card_bloque.wait_for(state="visible", timeout=8000)

            t_inicio = time.time()
            reserva_confirmada = False

            # Monitoreo activo de apertura durante los primeros segundos
            while time.time() - t_inicio < 15:
                texto_card = card_bloque.inner_text().lower()

                # PROTECCIÓN 1: Si ya dice "cancelar", el cupo está tomado. Detenerse inmediatamente.
                if "cancelar" in texto_card:
                    print("¡Éxito! El cupo ya está tomado ('Cancelar Reserva' detectado). No se volverá a presionar.")
                    reserva_confirmada = True
                    break

                btn_accion = card_bloque.locator("button, [role='button']")
                if btn_accion.count() > 0:
                    texto_btn = btn_accion.first.inner_text().lower()

                    if "cancelar" in texto_btn:
                        print("¡Éxito! Botón en estado 'Cancelar Reserva'. Proceso finalizado.")
                        reserva_confirmada = True
                        break

                    # Si el servidor aún tarda una fracción de segundo en abrir
                    if "cerrado" in texto_btn:
                        time.sleep(0.15)
                        continue

                    # PROTECCIÓN 2: Si está abierto (no dice 'cerrado' y no dice 'cancelar'), reservar
                    print(f"¡Cupo abierto! (Texto: '{texto_btn}'). Enviando clic único de reserva...")
                    btn_accion.first.click(force=True)

                    # Espera pasiva de confirmación (sin volver a cliquear)
                    print("Esperando confirmación del servidor...")
                    for _ in range(20):  # Monitorear cada 150 ms durante 3 segundos
                        time.sleep(0.15)
                        if "cancelar" in card_bloque.inner_text().lower():
                            print("¡Confirmación recibida! El botón cambió a 'Cancelar Reserva'.")
                            reserva_confirmada = True
                            break

                    if reserva_confirmada:
                        break

                time.sleep(0.1)

            if not reserva_confirmada:
                print("Ciclo finalizado. Revisa la captura para confirmar el estado.")

            time.sleep(1)
            page.screenshot(path="comprobante_reserva.png")
            print("Captura guardada en comprobante_reserva.png")

        except Exception as e:
            print(f"\n[ALERTA] Error durante el proceso: {e}")
            page.screenshot(path="error_pantalla.png")
            raise e

        finally:
            browser.close()

if __name__ == "__main__":
    main()
