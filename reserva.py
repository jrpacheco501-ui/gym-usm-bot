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

            print("2. Iniciando sesión...")
            page.fill("input[type='email']", EMAIL)
            page.fill("input[type='password']", PASSWORD)
            
            # Enviar formulario
            page.press("input[type='password']", "Enter")
            time.sleep(1)
            btn_submit = page.locator("button[type='submit'], form button").filter(has_text=re.compile(r"iniciar", re.I))
            if btn_submit.count() > 0:
                btn_submit.last.click(force=True)

            print("Esperando modal de advertencia...")
            # 3. Cerrar el modal haciendo clic específicamente en el botón púrpura 'ENTENDIDO'
            btn_entendido = page.locator("button").filter(has_text=re.compile(r"^ENTENDIDO$", re.I))
            if btn_entendido.count() == 0:
                btn_entendido = page.get_by_text("ENTENDIDO", exact=True)
            
            btn_entendido.first.wait_for(state="visible", timeout=12000)
            btn_entendido.first.click()
            print("Botón ENTENDIDO presionado.")

            # Esperar a que el modal desaparezca por completo de la pantalla
            btn_entendido.first.wait_for(state="hidden", timeout=5000)
            print("Modal cerrado exitosamente.")
            time.sleep(1)

            # 4. Seleccionar sede San Joaquín
            print("Seleccionando sede San Joaquín...")
            tab_sj = page.locator("button, a, div").filter(has_text=re.compile(r"^San Joaqu[ií]n", re.I)).first
            tab_sj.wait_for(state="visible", timeout=8000)
            tab_sj.click()
            print("Sede San Joaquín seleccionada.")
            time.sleep(1)

            # 5. Espera activa hasta las 06:30:00 AM
            esperar_a_las_630()

            # 6. Al dar las 6:30:00, refrescar la lista de horarios pinchando San Joaquín
            print("Refrescando disponibilidad de bloques...")
            try:
                tab_sj.click(force=True)
                time.sleep(0.3)
            except Exception:
                pass

            # 7. Buscar y pinchar el Bloque 1-2 (08:15)
            print("Buscando Bloque 1-2 (08:15)...")
            card_bloque = page.locator("div").filter(has_text="08:15").filter(has_text="Bloque 1-2").last
            card_bloque.wait_for(state="visible", timeout=5000)

            # Reintento rápido de clic (hasta 5 segundos) por si el estado 'Bloque cerrado' tarda décimas en cambiar
            t_inicio = time.time()
            click_exitoso = False
            while time.time() - t_inicio < 5:
                # Si dentro de la tarjeta hay un botón activo
                btn_accion = card_bloque.locator("button, [role='button']")
                if btn_accion.count() > 0:
                    texto_btn = btn_accion.first.inner_text().lower()
                    if "cerrado" not in texto_btn:
                        btn_accion.first.click(force=True)
                        print(f"¡Botón de reserva presionado! (Texto: {texto_btn})")
                        click_exitoso = True
                        break
                
                # Como alternativa directa, hacer clic en la tarjeta misma
                card_bloque.click(force=True)
                time.sleep(0.3)

            if not click_exitoso:
                print("Se ejecutó clic sobre la tarjeta del bloque 1-2.")

            # Esperar 2 segundos para que la página procese la reserva
            time.sleep(2)
            page.screenshot(path="comprobante_reserva.png")
            print("Captura final guardada en comprobante_reserva.png")

        except Exception as e:
            print(f"\n[ALERTA] Error durante el proceso: {e}")
            page.screenshot(path="error_pantalla.png")
            raise e

        finally:
            browser.close()

if __name__ == "__main__":
    main()
