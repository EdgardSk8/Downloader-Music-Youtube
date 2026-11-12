import urllib.request
import urllib.parse
import json
import subprocess
import sys
import tempfile
import shutil
import os
import queue
import re
import socket
import yt_dlp
# import mimetypes
import threading
import time
import uuid
from flask import Flask, render_template, request, send_file, jsonify, after_this_request
from mutagen.mp4 import MP4, MP4Cover # MP4Cover sirve para incrustar la carátula (portada) 1:1
from version import VERSION

app = Flask(__name__) # Crea la instancia de la aplicación Flask

# La consola de Windows (cp1252) no puede imprimir ✔/✘ y lanzaría UnicodeEncodeError.
# Forzar UTF-8 en la salida evita que un simple print tumbe un hilo de descarga.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Carpeta final de las canciones: Descargas\DownloaderMusic
# Si la carpeta no existe se crea al arrancar; si ya existe se reutiliza (exist_ok=True).
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "DownloaderMusic")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
###################################################################

# -------------------------------------------------------------------------------------------------
# Estado de las descargas: cola + registro para la interfaz
# -------------------------------------------------------------------------------------------------

# Cola FIFO: cada pedido entra aquí y un ÚNICO hilo trabajador lo procesa en orden.
# Así se pueden encolar varias canciones sin esperar a que termine la anterior.
cola_descargas = queue.Queue()

# Registro central de descargas. Clave = task_id.
# Estados posibles: "cola" -> "descargando" -> "descargado" | "error"
descargas = {}

# Candado para que los hilos de Flask y el trabajador no modifiquen el registro a la vez.
descargas_lock = threading.Lock()

# El hilo trabajador se crea UNA sola vez (el reloader de Flask importa el módulo dos veces).
_worker_iniciado = False
_worker_lock = threading.Lock()


def _actualizar_descarga(task_id: str, **campos):
    """Actualiza campos concretos de una descarga de forma segura entre hilos."""
    cambio_estado = False

    with descargas_lock:
        if task_id in descargas:
            anterior = descargas[task_id].get("estado")
            descargas[task_id].update(campos)
            # Solo se guarda en disco cuando el estado CAMBIA (el progreso no se persiste)
            cambio_estado = "estado" in campos and campos["estado"] != anterior

    if cambio_estado:
        _guardar_historial()


def _leer_descarga(task_id: str):
    """Devuelve una COPIA de la descarga (para no exponer el diccionario interno)."""
    with descargas_lock:
        tarea = descargas.get(task_id)
        return dict(tarea) if tarea else None


def _listar_descargas():
    """Devuelve copias de todas las descargas registradas."""
    with descargas_lock:
        return [dict(tarea) for tarea in descargas.values()]


# -------------------------------------------------------------------------------------------------
# Historial persistente: sobrevive a reinicios y al reloader de Flask.
# Se guarda en %APPDATA%\DownloaderMusic\historial.json y se limita a las últimas 100 tareas.
# -------------------------------------------------------------------------------------------------
MAX_HISTORIAL = 100


def _ruta_historial() -> str:
    """Carpeta de datos del usuario donde se guarda historial.json."""
    base = os.getenv("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    carpeta = os.path.join(base, "DownloaderMusic")
    os.makedirs(carpeta, exist_ok=True)
    return os.path.join(carpeta, "historial.json")


HISTORIAL_PATH = _ruta_historial()


def _guardar_historial():
    """Escribe en disco las últimas tareas (se llama al cambiar de estado)."""
    with descargas_lock:
        tareas = sorted(
            (dict(tarea) for tarea in descargas.values()),
            key=lambda t: t.get("creada") or 0,
        )[-MAX_HISTORIAL:]

    try:
        with open(HISTORIAL_PATH, "w", encoding="utf-8") as archivo:
            json.dump(tareas, archivo, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[✘] No se pudo guardar el historial: {e}")


def _cargar_historial():
    """Recupera el historial guardado y marca como error las tareas interrumpidas."""
    try:
        with open(HISTORIAL_PATH, "r", encoding="utf-8") as archivo:
            tareas = json.load(archivo)
    except FileNotFoundError:
        return
    except Exception as e:
        print(f"[✘] No se pudo leer el historial: {e}")
        return

    with descargas_lock:
        for tarea in tareas:
            if not isinstance(tarea, dict) or not tarea.get("id"):
                continue

            if tarea.get("estado") in ("cola", "descargando", "procesando"):
                # La app se cerró/reinició a mitad de la descarga
                tarea["estado"] = "error"
                tarea["error"] = "Se interrumpió al cerrar la aplicación."
                tarea["finalizada"] = tarea.get("finalizada") or time.time()

            descargas[tarea["id"]] = tarea


_cargar_historial()  # Al arrancar se recupera el historial anterior


# yt-dlp colorea sus mensajes con códigos ANSI; se quitan para mostrarlos limpios en la interfaz.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _mensaje_error(error: Exception) -> str:
    """Convierte una excepción en texto plano (sin colores ANSI ni espacios sobrantes)."""
    return _ANSI_RE.sub("", str(error)).strip()


# Nombres de los postprocesadores de yt-dlp traducidos para mostrarlos en la interfaz.
# Se usan cuando la descarga termina y empieza la parte que NO es descarga (convertir, etiquetas…).
_NOMBRES_POSTPROCESADORES = {
    # yt-dlp reporta el nombre SIN el prefijo "FFmpeg" (ExtractAudio, Metadata, MoveFiles…)
    "ExtractAudio": "Convirtiendo a M4A…",
    "Metadata": "Escribiendo metadatos…",
    "MoveFiles": "Moviendo archivo…",
    "EmbedThumbnail": "Incrustando carátula…",
    # Compatibilidad con versiones que sí reportan el nombre completo
    "FFmpegExtractAudio": "Convirtiendo a M4A…",
    "FFmpegMetadata": "Escribiendo metadatos…",
    "ModifyChapters": "Procesando capítulos…",
    "FFmpegVideoRemuxer": "Remuxeando audio…",
}


def _marcar_procesando(task_id: str, datos: dict):
    """Marca la tarea como 'procesando' cuando yt-dlp entra en un postprocesador."""
    etapa = _NOMBRES_POSTPROCESADORES.get(
        datos.get("postprocessor", ""),
        "Procesando audio…",
    )
    _actualizar_descarga(
        task_id,
        estado="procesando",   # Ya no descarga bytes: está convirtiendo/etiquetando
        porcentaje=100,
        eta=0,
        speed=0,
        etapa=etapa,
    )

# -------------------------------------------------------------------------------------------------------------------------------- #

# -------------------------------------------------------------------------------------------------
# Actualizaciones automáticas (GitHub Releases)
# -------------------------------------------------------------------------------------------------
GITHUB_REPO = "EdgardSk8/Downloader-Music-Youtube"
URL_ULTIMA_RELEASE = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
URL_VERSION_JSON = f"https://raw.githubusercontent.com/{GITHUB_REPO}/refs/heads/main/version.json"
_USER_AGENT_ACTUALIZACION = "DownloaderMusicYoutube"

# Progreso de la descarga de la nueva versión (lo consulta el frontend)
estado_actualizacion = {
    "estado": "inactiva",  # inactiva | descargando | lista | error
    "porcentaje": 0,
    "descargado": 0,
    "total": 0,
    "error": None,
    "version": "",
}
estado_actualizacion_lock = threading.Lock()


def _leer_json_remoto(url: str, timeout: int = 8) -> dict:
    """GET a una URL de GitHub y devuelve el JSON (con User-Agent obligatorio)."""
    peticion = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT_ACTUALIZACION,
            "Accept": "application/vnd.github+json",
        },
    )

    with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def _version_de_texto(texto) -> tuple[int, ...]:
    """'v1.1.5' o 'Downloader Music Youtube v1.1.5' → (1, 1, 5)."""
    coincidencia = re.search(r"v?(\d+(?:\.\d+){1,2})", str(texto or ""))

    if not coincidencia:
        return ()

    partes = [int(p) for p in coincidencia.group(1).split(".")]
    return tuple(partes + [0] * (3 - len(partes)))  # Siempre 3 tramos


def _version_release(release: dict) -> str:
    """Versión de la Release: la mayor entre el TAG y el nombre.

    GitHub deja elegir tag y título por separado (el repo llegó a tener tag
    v1.0.5 con título v1.1.5); se toma la mayor para no perder actualizaciones.
    """
    candidatas = [release.get("tag_name"), release.get("name")]
    versiones = [v for v in (_version_de_texto(c) for c in candidatas) if v]

    return ".".join(str(p) for p in max(versiones)) if versiones else ""


def _info_actualizacion() -> dict:
    """Última versión publicada en GitHub: {version, url, mensaje, tamano}.

    La API de Releases es la fuente principal; si falla (sin internet o límite de
    peticiones) se usa version.json de la rama main como respaldo.
    """
    try:
        release = _leer_json_remoto(URL_ULTIMA_RELEASE)

        exe = next(
            (
                asset
                for asset in release.get("assets", [])
                if str(asset.get("name", "")).lower().endswith(".exe")
            ),
            None,
        )
        version = _version_release(release)

        if exe and version:
            return {
                "version": version,
                "url": exe.get("browser_download_url", ""),
                "mensaje": (release.get("body") or "").strip(),
                "tamano": exe.get("size") or 0,
            }

    except Exception as e:
        print(f"[!] No se pudo consultar GitHub Releases: {_mensaje_error(e)}")

    try:
        respaldo = _leer_json_remoto(URL_VERSION_JSON, timeout=5)
        version = _version_de_texto(respaldo.get("version"))

        return {
            "version": ".".join(str(p) for p in version) if version else VERSION,
            "url": respaldo.get("url", ""),
            "mensaje": respaldo.get("mensaje", ""),
            "tamano": 0,
        }

    except Exception:
        return {"version": VERSION, "url": "", "mensaje": "", "tamano": 0}


def _marcar_actualizacion(**campos):
    with estado_actualizacion_lock:
        estado_actualizacion.update(campos)


def _leer_estado_actualizacion() -> dict:
    with estado_actualizacion_lock:
        return dict(estado_actualizacion)


def _descargar_con_progreso(url: str, destino: str):
    """Descarga la nueva versión en streaming y va publicando el progreso."""
    peticion = urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT_ACTUALIZACION},
    )

    with urllib.request.urlopen(peticion, timeout=30) as respuesta, open(destino, "wb") as archivo:
        total = int(respuesta.headers.get("Content-Length") or 0)
        descargado = 0

        if total:
            _marcar_actualizacion(total=total)

        while True:
            bloque = respuesta.read(64 * 1024)

            if not bloque:
                break

            archivo.write(bloque)
            descargado += len(bloque)

            porcentaje = min(100.0, descargado * 100 / total) if total else 0
            _marcar_actualizacion(
                porcentaje=round(porcentaje, 1),
                descargado=descargado,
            )


def _proceso_actualizacion(url: str, version: str, tamano: int, updater: str):
    """Descarga el .exe nuevo, lanza updater.exe y cierra la app."""
    carpeta = os.path.join(tempfile.gettempdir(), "DownloaderMusicUpdate")
    os.makedirs(carpeta, exist_ok=True)

    destino = os.path.join(carpeta, "nueva_version.exe")
    parcial = destino + ".part"

    try:
        if os.path.exists(parcial):
            os.remove(parcial)

        _descargar_con_progreso(url, parcial)

        peso = os.path.getsize(parcial)

        if tamano and peso != tamano:
            raise Exception(f"El archivo pesa {peso} bytes y se esperaban {tamano}")

        with open(parcial, "rb") as archivo:
            if archivo.read(2) != b"MZ":
                raise Exception("El archivo descargado no es un .exe válido")

        os.replace(parcial, destino)

        # Limpia copias de updater.exe de actualizaciones anteriores
        for nombre in os.listdir(carpeta):
            if nombre.startswith("updater-") and nombre.endswith(".exe"):
                try:
                    os.remove(os.path.join(carpeta, nombre))
                except OSError:
                    pass

        # Copia del updater fuera de _MEIPASS (esa carpeta se borra al cerrar la app)
        updater_local = os.path.join(carpeta, f"updater-{uuid.uuid4().hex[:8]}.exe")
        shutil.copyfile(updater, updater_local)

        _marcar_actualizacion(
            estado="lista",
            porcentaje=100,
            descargado=peso,
            version=version,
        )

        subprocess.Popen([updater_local, destino, sys.executable], cwd=carpeta)

        # Da tiempo a mostrar "Reiniciando…" en la interfaz y cierra la app
        threading.Timer(2.0, lambda: os._exit(0)).start()

    except Exception as e:
        _marcar_actualizacion(estado="error", error=_mensaje_error(e))
        print(f"[✘] Error al actualizar: {_mensaje_error(e)}")

# -------------------------------------------------------------------------------------------------------------------------------- #

@app.route("/version")
def version():
    return jsonify({"version": VERSION})


@app.route("/carpeta") # Ruta de la carpeta donde se guardan las canciones
def carpeta():
    return jsonify({"carpeta": DOWNLOAD_DIR})


@app.route("/abrir-carpeta", methods=["POST"]) # Abre la carpeta en el Explorador
def abrir_carpeta():
    try:
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)  # Por si se borró con la app abierta

        if sys.platform == "win32":
            os.startfile(DOWNLOAD_DIR)  # Abre el Explorador de Windows en esa carpeta
        elif sys.platform == "darwin":
            subprocess.Popen(["open", DOWNLOAD_DIR])
        else:
            subprocess.Popen(["xdg-open", DOWNLOAD_DIR])

        return jsonify({"ok": True, "carpeta": DOWNLOAD_DIR})

    except Exception as e:
        return jsonify({"error": _mensaje_error(e)}), 500


@app.route("/actualizacion")
def actualizacion():
    # 0.0.0 es la versión de desarrollo: no se buscan actualizaciones para no molestar
    # en pruebas. Cualquier build publicada (0.0.1, 1.0.0…) sí las busca.
    if VERSION == "0.0.0":
        return jsonify({"version": VERSION, "url": "", "mensaje": "", "tamano": 0})

    return jsonify(_info_actualizacion())
# -------------------------------------------------------------------------------------------------------------------------------- #

def obtener_info(url: str) -> dict: # Funcion para obtener la informacion del video
    ydl_opts = {"quiet": True, "noplaylist": True} # Define las opciones de configuración (silencio y sin playlists).
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: # Crea una instancia del descargador con esas opciones.
        info = ydl.extract_info(url, download=False) # Obtiene los metadatos del video sin descargarlo.

    return {
        "title": info.get("title", "cancion"), # Obtiene el titulo del URl
        "duration": info.get("duration", 0), # Duracion
        "thumbnail": info.get("thumbnail", ""), # Miniatura
        "uploader": info.get("uploader", "Desconocido"), # Canal de quien subio el video
    }


@app.route("/actualizar", methods=["POST"])
def actualizar():
    if not getattr(sys, "frozen", False):
        return jsonify({
            "error": "La actualización automática solo funciona en el .exe"
        }), 400

    datos = request.get_json(silent=True) or {}
    url = (datos.get("url") or "").strip()
    version = (datos.get("version") or "").strip()
    tamano = int(datos.get("tamano") or 0)

    if not url:
        return jsonify({
            "error": "No se proporcionó la URL de actualización"
        }), 400

    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if host != "github.com" and not host.endswith(".github.com"):
        return jsonify({
            "error": "La actualización solo se descarga desde GitHub"
        }), 400

    updater = os.path.join(getattr(sys, "_MEIPASS", ""), "updater.exe")
    if not os.path.isfile(updater):
        return jsonify({
            "error": "La aplicación no incluye updater.exe"
        }), 500

    with estado_actualizacion_lock:
        if estado_actualizacion["estado"] == "descargando":
            return jsonify({"error": "Ya hay una actualización en curso"}), 409

        estado_actualizacion.update({
            "estado": "descargando",
            "porcentaje": 0,
            "descargado": 0,
            "total": tamano,
            "error": None,
            "version": version,
        })

    threading.Thread(
        target=_proceso_actualizacion,
        args=(url, version, tamano, updater),
        daemon=True,
        name="actualizacion",
    ).start()

    return jsonify({"ok": True})


@app.route("/actualizar/progreso")  # Progreso de la descarga de la nueva versión
def progreso_actualizacion():
    return jsonify(_leer_estado_actualizacion())
# -------------------------------------------------------------------------------------------------------------------------------- #

# def limpiar_archivo(filepath: str, delay: int = 5): # Funcion que borra un archivo con un retrado de 5 segundos
#     def _remove(path):
#         time.sleep(delay) # Espera 5 seg en delay
#         try: os.remove(path); print(f"\n[✔] Eliminado: {path}\n") # Intenta eliminar el archivo, en caso de ser exitoso mostrar el primer mensaje
#         except Exception as e: print(f"[✘] No se pudo eliminar {path}: {e}") # Del caso contrario mostrar 
#     threading.Thread(target=_remove, args=(filepath,), daemon=True).start() # En caso de fallar mostrar detalladamente el error

# -------------------------------------------------------------------------------------------------------------------------------- #

# Define la función, recibe URL, ID de tarea y carpeta destino
#def descargar_audio_con_progreso(url: str, task_id: str, carpeta="temp") -> tuple[str, dict]:
 #   os.makedirs(carpeta, exist_ok=True) # Crea una carpeta, en caso que no exista crearla
   # output_path = os.path.join(carpeta, "%(title)s.%(ext)s") # Ruta de salida con nombre según título y extensión

def _muestrear_progreso(task_id: str, ruta_temporal: str):
    """Suaviza la barra leyendo el tamaño real del archivo temporal cada 0,1 s.

    yt-dlp solo llama al hook de progreso una vez por bloque descargado (hasta 4 MB),
    así que en canciones pequeñas el % salta de 0 a 100 de golpe. Este muestreo da
    valores intermedios sin tocar el downloader. Termina solo cuando la tarea deja
    de estar en "descargando" (pasa a procesando/descargado/error).
    """
    if not ruta_temporal:
        return

    anterior_tamano = None
    anterior_tiempo = time.monotonic()
    velocidad = 0.0

    while True:
        time.sleep(0.1)

        tarea = _leer_descarga(task_id)

        if not tarea or tarea.get("estado") != "descargando":
            return

        total = tarea.get("total") or 0
        if total <= 0:
            continue  # Todavía no se conoce el tamaño total

        try:
            descargado = os.path.getsize(ruta_temporal)
        except OSError:
            continue  # El .part aún no existe o ya se renombró

        ahora = time.monotonic()

        if anterior_tamano is not None:
            intervalo = ahora - anterior_tiempo
            if intervalo > 0:
                muestra = max(0.0, (descargado - anterior_tamano) / intervalo)
                # Media móvil: evita que la velocidad parpadee cada 0,1 s
                velocidad = muestra if velocidad <= 0 else (velocidad * 0.7 + muestra * 0.3)

        anterior_tamano = descargado
        anterior_tiempo = ahora

        porcentaje = min(100.0, descargado / total * 100)
        restante = max(0, total - descargado)
        eta = int(restante / velocidad) if velocidad > 0 else 0

        _actualizar_descarga(
            task_id,
            porcentaje=round(porcentaje, 2),
            descargado=descargado,
            speed=round(velocidad),
            eta=eta,
        )


def descargar_audio_con_progreso(url: str, task_id: str) -> tuple[str, dict]:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)  # Recrea la carpeta si se borró con la app abierta
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    hilo_muestreo = None  # Se crea una sola vez, en el primer aviso de descarga

    def progreso_hook(d): # Funcion que actualiza el proceso de descarga
        nonlocal hilo_muestreo

        if d['status'] == 'downloading': # Si el estado de descarga es "Downloanding"
            porcentaje = 0 # Inicializador en 0
            if d.get('total_bytes'): # Verificacion del tamanio total
                porcentaje = d['downloaded_bytes'] / d['total_bytes'] * 100 # Calcular % 

            # Guarda el avance en el registro central (lo lee el endpoint /descargas)
            _actualizar_descarga(
                task_id,
                estado="descargando",
                porcentaje=round(porcentaje, 4), # % con 4 decimales
                descargado=d.get('downloaded_bytes', 0), # Bytes descargados
                total=d.get('total_bytes', 0), # Tamaño total
                eta=d.get('eta', 0), # Tiempo estimado
                speed=d.get('speed', 0), # Velocidad de descarga
            )

            # Primer aviso: arranca el muestreo del .part para que la barra no salte
            if hilo_muestreo is None:
                ruta_temporal = d.get("tmpfilename") or (
                    f"{d['filename']}.part" if d.get("filename") else ""
                )

                hilo_muestreo = threading.Thread(
                    target=_muestrear_progreso,
                    args=(task_id, ruta_temporal),
                    daemon=True,
                    name=f"progreso-{task_id[:8]}",
                )
                hilo_muestreo.start()

        elif d['status'] == 'finished':
            # Los bytes YA se descargaron; ahora yt-dlp pasa a convertir/etiquetar.
            # Este es el tiempo de espera que el usuario notaba antes del archivo final.
            _actualizar_descarga(
                task_id,
                estado="procesando",
                porcentaje=100,
                eta=0,
                speed=0,
                etapa="Preparando conversión…",
            )

    def postproceso_hook(d): # Avisa al empezar cada postprocesador (convertir, etiquetas, carátula)
        if d.get('status') in ("started", "processing"):
            _marcar_procesando(task_id, d)
    ydl_opts = {
        "format": "bestaudio",
        "outtmpl": output_path,
        "quiet": True,
        "noplaylist": True,
        "progress_hooks": [progreso_hook],
        # Hook de postprocesado: permite mostrar "Convirtiendo…" después de descargar
        "postprocessor_hooks": [postproceso_hook],

        "cookiefile": "cookies.txt",

        # Ya no se usa "writethumbnail": la portada se prepara a mano en 1:1 con _preparar_portada

        # 🔥 CLAVE: JS runtime
        "js_runtimes": {
            "node": {
                "executable_path": "C:\\Program Files\\nodejs\\node.exe"
            }
        },

        # 🔥 CLAVE: solver de YouTube (ARREGLA 403)
        "remote_components": ["ejs:github"],

        # 🔥 CLAVE: cliente alternativo


        # 🔥 headers anti bloqueo
        "http_headers": {
            "User-Agent": "com.google.android.youtube/17.31.35 (Linux; U; Android 11)"
        },

        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
            },
            {
                "key": "FFmpegMetadata",
                "add_metadata": True
            },
            # EmbedThumbnail se quitó a propósito: incrustaba la miniatura 16:9 original.
            # Ahora _preparar_portada crea una carátula 1:1 de 1200x1200 y la escribe con mutagen.
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)  # Descargar el video/audio y obtener su información
        filepath = ydl.prepare_filename(info) # Generar la ruta final del archivo descargado
        filepath = os.path.splitext(filepath)[0] + ".m4a"

    return filepath, info # Retorna la ruta del archivo y los metadatos del video

# -------------------------------------------------------------------------------------------------------------------------------- #

def _componer_nombre(titulo: str, autor: str) -> str:
    """Aplica la regla del nombre: si NO hay guion, se antepone "Autor - ".

    - Si el título ya trae guion, se respeta tal cual (la izquierda es el autor).
    - Se limpian los "#" iniciales (títulos tipo "## Canción").
    - Del autor se quita el sufijo " - Topic" de los canales automáticos de YouTube.
    """
    titulo = re.sub(r"^[#\s]+", "", (titulo or "").strip())

    if "-" in titulo:
        return titulo

    # "Autor - Topic" son canales automáticos; "@usuario" viene de uploader_id
    autor = re.sub(r"\s*-\s*topic$", "", (autor or "").strip(), flags=re.IGNORECASE)
    autor = autor.lstrip("@").strip()

    if not autor:
        return titulo

    return f"{autor} - {titulo}"


def _mejor_miniatura(info: dict) -> str:
    """Devuelve la URL de la miniatura de mayor resolución disponible."""
    miniaturas = info.get("thumbnails") or []
    validas = [m for m in miniaturas if m.get("url")]

    if validas:
        mejor = max(validas, key=lambda m: (m.get("width") or 0) * (m.get("height") or 0))
        return mejor["url"]

    return info.get("thumbnail", "")


def _preparar_portada(info: dict):
    """Descarga la miniatura y la recorta a 1:1 en 1200x1200 (óptimo para Apple Music).

    Devuelve los bytes JPEG listos para incrustar, o None si algo falla.
    Usa FFmpeg (ya es obligatorio para convertir a .m4a), así no hace falta Pillow.
    """
    url = _mejor_miniatura(info)
    if not url:
        return None

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("[!] FFmpeg no está en PATH: no se puede preparar la portada")
        return None

    try:
        with tempfile.TemporaryDirectory() as carpeta_temporal:
            original = os.path.join(carpeta_temporal, "miniatura")
            portada = os.path.join(carpeta_temporal, "portada.jpg")

            urllib.request.urlretrieve(url, original)  # Descarga la miniatura original

            # Recorte centrado al lado menor y escalado Lanczos a 1200x1200 (calidad alta)
            subprocess.run(
                [
                    ffmpeg, "-y", "-i", original,
                    "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=1200:1200:flags=lanczos",
                    "-q:v", "2",  # Calidad JPEG 2 (muy alta)
                    "-frames:v", "1",
                    portada,
                ],
                check=True,
                capture_output=True,
            )

            with open(portada, "rb") as archivo:
                return archivo.read()

    except Exception as e:
        print(f"[✘] No se pudo preparar la portada 1:1: {e}")
        return None


def _escribir_metadatos(filepath: str, base_title: str, portada: bytes | None = None):
    """Escribe artista, título y (si hay) la carátula 1:1 en el .m4a."""
    # Si el nombre trae un guion se interpreta como "Artista - Título"
    if "-" in base_title:
        artist, title = [x.strip() for x in base_title.split("-", 1)]  # Divide en dos partes (artista - título)
    else:
        artist, title = "Desconocido", base_title  # Si no hay guion, usa todo como título

    print(f"\n[INFO] Archivo procesado:\n")  # Mensaje de información
    print(f"       Artista: {artist}")  # Muestra el artista detectado
    print(f"       Título : {title}")  # Muestra el título detectado
    print(f"       Nombre final: {base_title}\n")  # Muestra el nombre completo final

    try:
        audio = MP4(filepath)  # Abre el archivo descargado como un contenedor MP4
        audio["\xa9ART"] = [artist]   # Inserta el metadato de artista
        audio["\xa9nam"] = [title]    # Inserta el metadato de título

        if portada:
            # covr = carátula embebida; MP4Cover la guarda como JPEG
            audio["covr"] = [MP4Cover(portada, imageformat=MP4Cover.FORMAT_JPEG)]

        audio.save()  # Guarda los cambios en el archivo
    except Exception as e:
        # Si falla solo se avisa: la descarga ya es válida y no se pierde el archivo
        print(f"[✘] No se pudieron escribir metadatos: {e}")


def _procesar_descarga(task_id: str): # Descarga una tarea concreta y actualiza su estado
    tarea = _leer_descarga(task_id)  # Copia de la tarea (url, título, estado actual)
    if not tarea:
        return

    url = tarea["url"]
    custom_title = tarea.get("custom_title") or ""

    # Marca la tarea como activa justo antes de empezar
    _actualizar_descarga(
        task_id,
        estado="descargando",
        iniciada=time.time(),
        error=None,
    )

    try:
        filepath, info = descargar_audio_con_progreso(url, task_id)  # Llama a la función de descarga y obtiene ruta e info del archivo

        # Autor: yt-dlp a veces deja uploader/channel vacíos en la descarga;
        # se usa el autor que mandó la interfaz y, como último recurso, uploader_id.
        autor = (
            info.get("uploader")
            or info.get("channel")
            or info.get("creator")
            or tarea.get("uploader")
            or info.get("uploader_id", "")
        )

        # Regla del nombre: si el título no trae guion, se antepone "Autor - "
        base_title = _componer_nombre(
            custom_title or info.get("title", "cancion"),
            autor,
        )

        # Mutagen es el último paso antes de dar el archivo por terminado
        _actualizar_descarga(task_id, estado="procesando", etapa="Preparando portada 1:1…")
        portada = _preparar_portada(info)  # Miniatura recortada a 1200x1200 (JPEG)

        _actualizar_descarga(task_id, estado="procesando", etapa="Guardando metadatos…")
        _escribir_metadatos(filepath, base_title, portada)  # Escribe artista, título y carátula

        # Éxito: archivo listo para el usuario (100 % y datos para el historial)
        _actualizar_descarga(
            task_id,
            estado="descargado",
            porcentaje=100,
            eta=0,
            speed=0,
            etapa=None,
            filepath=filepath,
            nombre_archivo=os.path.basename(filepath),
            custom_title=base_title,
            finalizada=time.time(),
        )

    except Exception as e:
        # Cualquier fallo deja la tarea como "error" con el mensaje para la interfaz
        _actualizar_descarga(
            task_id,
            estado="error",
            error=_mensaje_error(e),
            finalizada=time.time(),
        )
        print(f"[✘] Error al descargar {url}: {_mensaje_error(e)}")


def _worker_descargas(): # Hilo ÚNICO que saca tareas de la cola y las procesa en orden
    while True:
        task_id = cola_descargas.get()  # Bloquea hasta que haya una tarea nueva
        try:
            _procesar_descarga(task_id)
        except Exception as e:
            # Red de seguridad: ninguna excepción debe matar al trabajador
            _actualizar_descarga(task_id, estado="error", error=_mensaje_error(e))
        finally:
            cola_descargas.task_done()


def _asegurar_worker(): # Inicia el hilo trabajador la primera vez que se encola algo
    global _worker_iniciado
    with _worker_lock:
        if not _worker_iniciado:
            threading.Thread(
                target=_worker_descargas,
                daemon=True,
                name="cola-descargas",
            ).start()
            _worker_iniciado = True

# -------------------------------------------------------------------------------------------------------------------------------- #

@app.route("/") # Define la ruta principal
def index(): return render_template("index.html") # Renderiza la vista Html

# -------------------------------------------------------------------------------------------------------------------------------- #

@app.route("/informacion", methods=["POST"]) # Definicion de EndPoint POST

def informacion():

    data = request.get_json() # Obtiene los datos enviados en formato JSON
    url = data.get("url") # Extrae el valor de "url" del JSON recibido

    if not url: return jsonify({"error": "No se proporcionó un enlace"}), 400 # Si no hay URL
    try: return jsonify(obtener_info(url)) # En caso de tener URL obtener su informacion y devolverla en formato json
    except Exception as e: return jsonify({"error": _mensaje_error(e)}), 500 # En caso de error en la funcion obtener_info

# -------------------------------------------------------------------------------------------------------------------------------- #

@app.route("/descargar", methods=["POST"]) # Definicion de EndPoint POST

def descargar():

    data = request.get_json(silent=True) or {} # Obtiene los datos enviados en formato JSON
    url = data.get("url") # Extrae el valor de "url" del JSON recibido
    custom_title = data.get("custom_title") # Extrae un título personalizado opcional
    uploader = data.get("uploader") # Autor que ya conoce la interfaz (respaldo para la regla)

    if not url: return jsonify({"error": "No se proporcionó un enlace"}), 400 # En caso de no proporcionar URL

    task_id = str(uuid.uuid4()) # Genera un ID único (Para diferenciar de las demás descargas)

    # Registra la tarea como "en cola" (todavía NO se descarga: la procesa el worker)
    with descargas_lock:
        descargas[task_id] = {
            "id": task_id,
            "url": url,
            "custom_title": custom_title or "",
            "uploader": uploader or "",
            "estado": "cola",        # cola -> descargando -> procesando -> descargado | error
            "etapa": None,           # Texto de la fase actual ("Convirtiendo a M4A…")
            "porcentaje": 0,
            "descargado": 0,
            "total": 0,
            "eta": 0,
            "speed": 0,
            "error": None,
            "filepath": None,
            "nombre_archivo": None,
            "creada": time.time(),
            "iniciada": None,
            "finalizada": None,
        }

    _guardar_historial()        # Persiste la tarea nueva como "cola"

    _asegurar_worker()          # Arranca el hilo trabajador solo la primera vez
    cola_descargas.put(task_id) # Encola el pedido (se procesará cuando le toque)

    return jsonify({"task_id": task_id}), 200 # Devuelve el ID de la tarea al cliente con estado 200

# -------------------------------------------------------------------------------------------------------------------------------- #

@app.route("/descargas") # Lista completa para pintar cola + historial en la interfaz

def listar_descargas():

    tareas = _listar_descargas()

    # "procesando" también es una tarea activa (convirtiendo/metadatos); si no se incluye,
    # desaparece de la interfaz justo durante la conversión.
    activas = [t for t in tareas if t["estado"] in ("descargando", "procesando")]
    en_cola = sorted(
        [t for t in tareas if t["estado"] == "cola"], # Esperando turno (FIFO)
        key=lambda t: t["creada"],
    )
    historial = sorted(
        [t for t in tareas if t["estado"] in ("descargado", "error")], # Terminadas (éxito o error)
        key=lambda t: t.get("finalizada") or t.get("creada"),
        reverse=True, # La más reciente primero
    )

    for posicion, tarea in enumerate(en_cola, start=1): # Posición visible: #1, #2...
        tarea["posicion"] = posicion

    return jsonify({
        "activas": activas,
        "cola": en_cola,
        "historial": historial,
        "total": len(tareas),
    })


@app.route("/descargas/<task_id>", methods=["DELETE"]) # Quita UNA tarea terminada del historial (el archivo NO se borra)
def eliminar_descarga(task_id):
    with descargas_lock:
        tarea = descargas.get(task_id)

        if not tarea:
            return jsonify({"error": "ID no encontrado"}), 404

        if tarea.get("estado") not in ("descargado", "error"):
            return jsonify({"error": "La descarga todavía está en curso"}), 409

        del descargas[task_id]  # Solo se quita del registro visual

    _guardar_historial()  # Persiste el historial sin esa tarea
    return jsonify({"ok": True})


@app.route("/historial", methods=["DELETE"]) # Quita TODO el historial (los archivos NO se borran)
def limpiar_historial():
    with descargas_lock:
        terminadas = [
            task_id
            for task_id, tarea in descargas.items()
            if tarea.get("estado") in ("descargado", "error")
        ]

        for task_id in terminadas:
            del descargas[task_id]

    _guardar_historial()
    return jsonify({"ok": True, "eliminadas": len(terminadas)})

# -------------------------------------------------------------------------------------------------------------------------------- #

@app.route("/progreso/<task_id>") # Definicion de ruta (<task_id> parametro dinamico)

def progreso(task_id):

    data = _leer_descarga(task_id) # Busca la tarea por su ID en el registro central

    if not data: return jsonify({"error": "ID no encontrado"}), 404 # Si no encuentra el ID devolver error
    return jsonify(data) # Devuelve el estado actual de la tarea en formato JSON

# -------------------------------------------------------------------------------------------------------------------------------- #

# @app.route("/download_file/<task_id>") # Definicion de ruta para descargar archivo final

# def download_file(task_id):
    
#     data = progreso_global.get(task_id) # Obtiene los datos de progreso de la tarea usando su ID

#     if not data or "filepath" not in data: return "Archivo no disponible", 404 # Si no existe la tarea devolver error

#     filepath = data["filepath"] # Ruta del archivo en el servidor
#     filename = data["custom_title"] + ".m4a" # Nombre nuevo asignado

#     @after_this_request # Decorador que ejecuta una función justo después de enviar la respuesta

#     def _remove_file(response):  # Función interna para eliminar el archivo después de enviarlo
#         limpiar_archivo(filepath)  # Llama a la función que borra el archivo en segundo plano
#         return response # Devuelve respuesta

#     mime_type, _ = mimetypes.guess_type(filepath)  # Detecta el tipo MIME del archivo según su extensión
#     return send_file(filepath, as_attachment=True, download_name=filename, mimetype=mime_type or "audio/mp4") # Envía el archivo como descarga, con el nombre correcto y el tipo MIME adecuado
#     # MIME = Extensiones de Correo de Internet Multipropósito
    # Se usa para decirle al navegador qué tipo de archivo está descargando, así puede manejarlo correctamente

# -----------------------#
# Run
# -----------------------#

if __name__ == "__main__": # Comprueba si este archivo se está ejecutando directamente
    # Evita abrir dos servidores a la vez: con dos instancias, el historial y el progreso
    # se dividen entre procesos y la interfaz parece "perder" las descargas.
    try:
        with socket.create_connection(("127.0.0.1", 5000), timeout=0.5):
            print("[!] Ya hay una instancia de la app usando el puerto 5000. Cierrala antes de iniciar otra.")
            sys.exit(1)
    except OSError:
        pass  # Puerto libre: es la primera instancia

    # use_reloader=False: un solo proceso estable (sin procesos hijos fantasma ni recargas
    # inesperadas que antes dividían el historial).
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

# Encender servicio con py app.py

# Actualizar en tonrno de yt-dlp con el comando: python -m pip install -U yt-dlp
# Nueva actualizacion: python.exe -m pip install --upgrade pip

# En caso de error desisntalar la version antigua e instalar la version nueva de yt-dlp

# Desinstarlar: py -m pip uninstall yt-dlp -y

# Instalar la nueva version: py -m pip install -U yt-dlp

# Verificar la version instalada: py -m yt_dlp --version

