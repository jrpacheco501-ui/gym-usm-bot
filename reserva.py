import os
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
            print(f"Hora actual ({ahora.strftime('%H:%M:%S')}) ya superó las 06:30 AM.")
            break
        time.sleep(0.15)  # Chequeo continuo cada 150 ms

def main():
    if not PASSWORD:
        print("Error: La variable GYM_PASSWORD no está configurada.")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        print("1. Accediendo a reservasgimnasiosantiago.cl...")
        page.goto("https://reservasgimnasiosantiago.cl/", wait_until="networkidle")

        print("2. Iniciando sesión...")
        page.fill("input[type='email']", EMAIL)
        page.fill("input[type='password']", PASSWORD)
        page.click("button:has-text('Iniciar sesión')")

        # 3. Cerrar popup inicial de advertencia
        try:
            print("Esperando modal de advertencia...")
            btn_entendido = page.wait_for_selector(
                "button:has-text('ENTENDIDO'), button:has-text('Entendido')",
                timeout=8000
            )
            if btn_entendido:
                btn_entendido.click()
                print("Modal cerrado.")
        except Exception:
            print("No se detectó el modal o ya estaba cerrado.")

        # 4. Seleccionar campus San Joaquín
        print("Seleccionando sede San Joaquín...")
        page.wait_for_selector("text=San Joaquín", timeout=8000)
        page.click("text=San Joaquín")
        time.sleep(1)

        # 5. Espera activa hasta exactamente las 6:30:00 AM
        esperar_a_las_630()

        # 6. Actualizar el estado de los bloques
        try:
            page.click("text=San Joaquín")
        except Exception:
            pass

        # 7. Clic inmediato sobre el Bloque 1-2 (8:15)
        print(f"Haciendo clic inmediato en el bloque {TARGET_BLOCK}...")
        try:
            selector = f"button:has-text('{TARGET_BLOCK}'), [role='button']:has-text('{TARGET_BLOCK}'), div:has-text('{TARGET_BLOCK}')"
            btn_bloque = page.wait_for_selector(selector, timeout=4000)
            if btn_bloque:
                btn_bloque.click(force=True)
                print("¡Cupo reservado exitosamente!")

            time.sleep(2)
            page.screenshot(path="comprobante_reserva.png")
            print("Comprobante guardado en comprobante_reserva.png.")
        except Exception as e:
            print(f"Error al presionar el bloque: {e}")
            page.screenshot(path="error_reserva.png")

        browser.close()

if __name__ == "__main__":
    main()