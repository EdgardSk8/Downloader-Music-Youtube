"""Aplica una actualización ya descargada y reinicia la aplicación.

Uso (lo lanza app.py):
    updater.exe <nueva_version.exe> <exe_actual>

Espera a que la app se cierre, reemplaza el .exe y la vuelve a abrir.
"""

import ctypes
import os
import subprocess
import sys
import time

LOG = os.path.join(os.environ.get("TEMP", "."), "DownloaderMusicUpdate", "updater.log")


def _log(mensaje: str):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as archivo:
            archivo.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {mensaje}\n")
    except Exception:
        pass


def _avisar(texto: str):
    """MessageBox: updater.exe se compila con console=False (sin consola)."""
    _log(texto)

    try:
        ctypes.windll.user32.MessageBoxW(
            None,
            texto,
            "Downloader Music Youtube",
            0x10,  # MB_ICONERROR
        )
    except Exception:
        pass


def _reemplazar(nuevo: str, actual: str, limite: float = 60.0) -> bool:
    """Reemplaza el .exe esperando a que Windows libere el archivo."""
    fin = time.time() + limite

    while time.time() < fin:
        try:
            os.replace(nuevo, actual)
            return True
        except PermissionError:
            time.sleep(0.5)  # La app aún se está cerrando
        except OSError as error:
            _log(f"Reintentando reemplazo: {error}")
            time.sleep(0.5)

    return False


def aplicar_actualizacion(nuevo: str, actual: str) -> int:
    if not os.path.isfile(nuevo):
        _avisar("No se encontró el archivo de la nueva versión.")
        return 1

    if not os.path.isfile(actual):
        _avisar("No se encontró la aplicación actual.")
        return 1

    with open(nuevo, "rb") as archivo:
        if archivo.read(2) != b"MZ":
            _avisar("El archivo descargado no es un ejecutable válido.")
            return 1

    if not _reemplazar(nuevo, actual):
        _avisar(
            "No se pudo reemplazar la aplicación (seguía abierta).\n"
            "Cierra la app y vuelve a intentarlo."
        )
        subprocess.Popen([actual], cwd=os.path.dirname(actual))
        return 1

    _log(f"Actualizado: {actual}")
    subprocess.Popen([actual], cwd=os.path.dirname(actual))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(1)

    sys.exit(aplicar_actualizacion(sys.argv[1], sys.argv[2]))
