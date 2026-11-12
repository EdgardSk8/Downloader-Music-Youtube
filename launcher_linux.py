"""Entrada para Linux: Flask en segundo plano + navegador (sin ventana nativa).

En Windows se usa `launcher.py` (pywebview). En Linux no hace falta GTK/WebKit:
se abre la interfaz en el navegador por defecto y el proceso queda vivo hasta Ctrl+C.
"""

import os
import socket
import sys
import threading
import time
import webbrowser

from app import app

HOST = "127.0.0.1"
PUERTO = int(os.environ.get("DOWNLOADER_PORT") or 5000)
URL = f"http://{HOST}:{PUERTO}"


def _servidor_listo() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conexion:
        conexion.settimeout(0.3)
        return conexion.connect_ex((HOST, PUERTO)) == 0


def _abrir_navegador(limite: float = 20.0):
    """Espera a que Flask escuche y abre el navegador (DOWNLOADER_NO_BROWSER=1 lo evita)."""
    fin = time.time() + limite

    while time.time() < fin:
        if _servidor_listo():
            if os.environ.get("DOWNLOADER_NO_BROWSER") != "1":
                webbrowser.open(URL)
            return

        time.sleep(0.2)


def main() -> int:
    if _servidor_listo():
        print(f"El puerto {PUERTO} ya está en uso. Abre {URL} o cierra la otra instancia.")
        return 1

    threading.Thread(
        target=lambda: app.run(host=HOST, port=PUERTO, debug=False, use_reloader=False),
        daemon=True,
        name="flask",
    ).start()

    _abrir_navegador()
    print(f"YouTube Music Downloader en {URL}  (Ctrl+C para salir)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
