import threading
import time
import os
import sys
import webview

from app import app


def iniciar_flask():
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )


def ruta_icono():
    """Icono de la ventana (en el .exe de PyInstaller vive en _MEIPASS)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    ruta = os.path.join(base, "Downloader-ico.ico")
    return ruta if os.path.isfile(ruta) else None


if __name__ == "__main__":
    threading.Thread(
        target=iniciar_flask,
        daemon=True
    ).start()

    time.sleep(1)

    webview.create_window(
        "Descargador de Música",
        "http://127.0.0.1:5000",
        width=900,
        height=600,
        resizable=True
    )

    webview.start(icon=ruta_icono())