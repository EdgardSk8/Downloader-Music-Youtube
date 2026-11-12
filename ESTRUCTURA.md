# 📚 ESTRUCTURA DEL PROYECTO — DownLoader Music Youtube

> **Propósito de este documento:** servir de mapa completo del proyecto antes de tocar cualquier
> archivo. Aquí se explica **qué hace cada archivo, por qué existe y qué se rompe si se cambia**.
>
> **Patrón del proyecto (IMPORTANTE):** el código está **muy comentado a propósito**, porque cada
> línea comentada corresponde a un error real que ya se corrigió (403 de YouTube, metadatos,
> progreso, empaquetado, etc.). **Al editar, mantener ese patrón**: no borrar comentarios
> existentes y comentar todo cambio nuevo con el motivo ("esto arregla X").
>
> Última revisión del documento: versión **0.0.0** de desarrollo ([version.py](./version.py)).

---

## 1. Resumen general

| Capa | Tecnología | Archivo(s) |
|------|-----------|------------|
| Backend (API + lógica de descarga) | Python + Flask + yt-dlp | [app.py](./app.py) |
| Ventana de escritorio (modo .exe) | pywebview (WebView2) | [launcher.py](./launcher.py) |
| Actualizador externo | Python (compilado aparte) | [updater.py](./updater.py) |
| Frontend | HTML + Bootstrap 5.3.3 + JS vanilla | [templates/index.html](./templates/index.html), [static/js/script.js](./static/js/script.js) |
| Versión visible | Archivo Python + JSON remoto | [version.py](./version.py), [version.json](./version.json) |
| Empaquetado | PyInstaller (one-file) | [Downloader Music Youtube v1.1.5.spec](./Downloader%20Music%20Youtube%20v1.1.5.spec), [build.spec](./build.spec), [updater.spec](./updater.spec) |

**Idea de arquitectura:** Flask no se abre en el navegador; `launcher.py` levanta Flask en
`127.0.0.1:5000` y abre una ventana nativa (pywebview) apuntando a esa URL. Todo el frontend se
comunica con el backend por `fetch()` a endpoints JSON. Las descargas pasan por una **cola FIFO**
(`queue.Queue`) que consume un **único hilo trabajador**, de modo que se pueden encolar varias
canciones sin esperar y el historial se pinta en la interfaz consultando `/descargas`.
El `.exe` final empaqueta `launcher.py` (junto con `templates/` y `static/`).

---

## 2. Entorno verificado (máquina actual)

| Elemento | Valor verificado | Nota |
|----------|------------------|------|
| Python | `3.14.7` en `.venv` | **Único entorno del proyecto** (`.venv-1` se eliminó el 12/11/2026) |
| Intérprete a usar | `.venv\Scripts\python.exe` | Tiene todas las dependencias instaladas |
| Flask | `3.1.3` | Servidor web |
| yt-dlp | `2026.8.19` | Motor de descarga (se actualiza aparte, ver §10) |
| mutagen | `1.48.1` | Escribe metadatos del `.m4a` |
| pywebview | `6.2.1` | Ventana nativa del .exe |
| PyInstaller | `6.22.3` (+ hooks-contrib `2026.8`) | Empaquetado |
| Node.js | `24.21.0` en `C:\Program Files\nodejs\node.exe` | **Ruta fija en app.py** (ver §11.2) |
| Node portable del repo | `node\node-v20.11.0-win-x64\node.exe` | **No lo usa nadie actualmente** |
| FFmpeg | En PATH: `C:\Users\Admin\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe` | **Obligatorio** para postprocesar a `.m4a` |
| Carpeta de salida | `%USERPROFILE%\Downloads` | Definida como `DOWNLOAD_DIR` en app.py |

> ⚠️ El Python global **no** tiene `yt_dlp` instalado. Si se ejecuta `python app.py` con el Python
> global fallará; usar siempre el intérprete de `.venv`.

---

## 3. Árbol de estructura comentado

```text
DownLoader Music Youtube/
│
├── app.py                  ← CEREBRO del proyecto. Flask + yt-dlp + metadatos + endpoints.
├── launcher.py             ← Punto de entrada del .exe. Levanta Flask en un hilo + ventana pywebview.
├── updater.py              ← Programa aparte que descarga e instala la nueva versión del .exe.
├── version.py              ← VERSION = "0.0.0"  (versión local que muestra la app).
├── version.json            ← Respaldo de /actualizacion: versión + URL directa del asset.
│
├── templates/
│   ├── index.html          ← Interfaz ÚNICA y ACTIVA (Flask la renderiza en "/").
│   └── index copy.html     ← Respaldo de la interfaz anterior. NO se usa, NO borrar sin permiso.
│
├── static/
│   ├── sinimagen.png       ← Imagen placeholder de la carátula (la usa index.html).
│   ├── Downloader-ico.png  ← Icono original (PNG 3977×4201) del que salen los demás.
│   ├── manifest.json       ← Web app manifest (Android/iPhone: nombre, colores e iconos).
│   ├── iconos/             ← Iconos generados: icon-32, icon-180 (Apple), icon-192,
│   │                          icon-512 e icon-maskable-512 (Android).
│   ├── js/script.js        ← Toda la lógica del cliente (fetch, progreso, modal, actualización).
│   └── css/
│       ├── descargas.css   ← ACTIVO: panel de descargas (scroll fino verde, textos, animaciones).
│       ├── style.css       ← ⚠️ LEGADO: index.html NO los carga (ver §4.7 y §11.7).
│       ├── style-resposive.css
│       ├── previews.css
│       └── previews-resposive.css
│
├── cookies.txt             ← 🚨 Cookies de sesión de YouTube para yt-dlp. ¡ESTÁ EN GIT Y PÚBLICO! (§11.1)
├── downloader.png          ← Imagen suelta en raíz. Sin uso desde el rediseño: el JS usa
│                             /static/sinimagen.png como respaldo.
├── Downloader-ico.ico      ← Icono del .exe (16→256 px, generado del PNG; lo usa el spec en `icon=`).
├── icono.ico               ← Icono del .exe de versiones anteriores (histórico).
├── icono.png               ← Icono antiguo de la raíz (ya no lo usa index.html).
│
├── Downloader Music Youtube v1.1.5.spec  ← Spec VIGENTE del .exe de la app (v1.1.5).
├── updater.spec                          ← Spec del updater.exe (compilación aparte).
├── build.spec                            ← Spec alternativo/antiguo (incluye pywebview y cookies.txt).
├── Descargador de Música.spec            ← ┐
├── Descargador-de-Musica.spec            │
├── Descargador.spec                      │ Specs históricos de versiones anteriores.
├── Downlader Music Youtube v1.1.3.spec   │ NO se usan para compilar la versión actual,
├── Downlader Music Youtube v1.1.4.spec   │ pero se conservan como historial.
├── Downloader Music Youtube V1.1.1.spec  │
├── Downloader Music Youtube V1.1.2.spec  │
├── Downloader Music Youtube v1.1.3.spec  │
└── Downloader Music Youtube.spec         ← ┘
│
├── apporiginal4.py         ← Respaldo de app.py ANTES de los cambios de producción
│                             (sin DOWNLOAD_DIR, sin actualizador). NO se ejecuta.
│
├── node/node-v20.11.0-win-x64/  ← Node portable versionado en git (70 MB). Hoy no se usa.
│
├── dist/                   ← Artefactos compilados (varios .exe de distintas versiones + updater.exe).
├── build/                  ← Carpetas temporales de PyInstaller (una por cada compilación).
├── temp/                   ← Vacía actualmente. Era la carpeta de descargas en desarrollo.
├── __pycache__/            ← Bytecode generado por Python. Versionado en git (no ideal, no crítico).
├── .venv/                  ← ÚNICO entorno virtual (dependencias instaladas). Es el que se debe usar.
└── .vscode/settings.json   ← Config del editor (Python env manager: system).
```

---

## 4. Fichas archivo por archivo

### 4.1 [app.py](./app.py) — Backend completo

**Qué es:** la aplicación Flask que contiene TODA la lógica del servidor. Se puede ejecutar solo
(`python app.py`) para desarrollo, pero para el .exe se importa desde `launcher.py`.

**Imports importantes y por qué están:**

| Import | Para qué se usa |
|--------|-----------------|
| `urllib.request`, `urllib.parse`, `json` | Consultar la API de Releases y descargar la actualización |
| `subprocess`, `sys`, `tempfile`, `shutil` | Lanzar el `updater.exe` en `/actualizar` |
| `yt_dlp` | Descargar audio y obtener info del video |
| `queue` | Cola FIFO de descargas (`queue.Queue`) |
| `re` | Quitar códigos de color ANSI de los errores de yt-dlp |
| `socket` | Comprobar que el puerto 5000 está libre (una sola instancia) |
| `threading` | Hilo trabajador de la cola + candados + cierre diferido de la app |

> Nota: al arrancar se fuerza UTF-8 en `sys.stdout`/`sys.stderr`; la consola de Windows (cp1252)
> no puede imprimir `✔`/`✘` y un `print()` fallido podía tumbar un hilo de descarga.
| `time` | Espera de 1 s antes de `os._exit(0)` |
| `uuid` | Generar `task_id` único por descarga |
| `flask` (`Flask`, `render_template`, `request`, `send_file`, `jsonify`, `after_this_request`) | Framework y utilidades (`send_file`/`after_this_request` solo para la ruta comentada) |
| `mutagen.mp4.MP4`, `MP4Cover` | Etiquetas `©ART`/`©nam` y carátula `covr` (JPEG 1200×1200) del `.m4a` |
| `version.VERSION` | Mostrar la versión local en `/version` |

**Variables globales / configuración:**

```python
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "DownloaderMusic")
# Las canciones se guardan DIRECTO en Descargas\DownloaderMusic (no se sirven por navegador).
# Si la carpeta no existe se crea; si existe se reutiliza (os.makedirs(..., exist_ok=True)).

cola_descargas = queue.Queue()     # Cola FIFO de task_id; la consume un ÚNICO hilo trabajador
descargas = {}                     # Registro central: {task_id: {url, custom_title, estado,
                                   #   etapa, porcentaje, descargado, total, eta, speed, error,
                                   #   filepath, nombre_archivo, creada, iniciada, finalizada}}
                                   # Estados: "cola" -> "descargando" -> "procesando"
                                   #          -> "descargado" | "error"
descargas_lock = threading.Lock()  # Protege el registro entre los hilos de Flask y el worker
_worker_iniciado = False           # El worker se crea una sola vez (protegido por _worker_lock)
_worker_lock = threading.Lock()

HISTORIAL_PATH = %APPDATA%\DownloaderMusic\historial.json  # Historial persistente (máx. 100 tareas)
```

**Mapa de endpoints (todos devuelven JSON):**

| Ruta | Método | Qué hace | Respuesta |
|------|--------|----------|-----------|
| `/` | GET | Renderiza `templates/index.html` | HTML |
| `/version` | GET | Devuelve la versión local | `{"version": "0.0.0"}` |
| `/carpeta` | GET | Ruta de la carpeta donde se guardan las canciones | `{"carpeta": "C:\\Users\\...\\Downloads\\DownloaderMusic"}` |
| `/abrir-carpeta` | POST | Crea la carpeta si falta y la abre en el Explorador (botón 📁 del navbar) | `{"ok": true, "carpeta"}` |
| `/actualizacion` | GET | Consulta la **última Release de GitHub** (API, con `version.json` como respaldo) | `{"version", "url", "mensaje", "tamano"}` |
| `/actualizar` | POST | **Solo en .exe**. Valida que la URL sea de GitHub, descarga el asset en un hilo (progreso en memoria) y, al terminar, lanza `updater.exe` y cierra la app | `{"ok": true}`; 400/409/500 |
| `/actualizar/progreso` | GET | Estado de la descarga de la nueva versión (lo consulta el modal) | `{"estado", "porcentaje", "descargado", "total", "error", "version"}` |
| `/informacion` | POST | Recibe `{"url"}` y devuelve metadatos SIN descargar | `{"title", "duration", "thumbnail", "uploader"}` |
| `/descargar` | POST | Recibe `{"url", "custom_title", "uploader"}`. Registra la tarea como `cola`, la encola y responde al instante | `{"task_id"}` |
| `/descargas` | GET | Devuelve todo agrupado (`activas` = `descargando` + `procesando`) | `{"activas", "cola", "historial", "total"}` |
| `/descargas/<task_id>` | DELETE | Quita **una** tarea terminada del historial (el archivo NO se borra). 404 si no existe, 409 si sigue en curso | `{"ok": true}` |
| `/historial` | DELETE | Quita **todas** las tareas terminadas del historial (los archivos NO se borran) | `{"ok": true, "eliminadas": N}` |
| `/progreso/<task_id>` | GET | Devuelve el estado actual de una tarea | `{estado, porcentaje, ...}` |
| `/download_file/<task_id>` | GET | **COMENTADA.** Servía el archivo al navegador y lo borraba con retardo. Ver §11.9 | — |

**Funciones clave:**

```python
obtener_info(url)                      # yt-dlp con download=False → metadatos para la vista previa
descargar_audio_con_progreso(url, id)  # descarga real + hook de progreso + postprocesado
_muestrear_progreso(task_id, .part)    # lee el tamaño del .part cada 0,1 s para suavizar la barra
_componer_nombre(titulo, autor)        # regla: sin guion → "Autor - Título"; con guion → tal cual
_mejor_miniatura(info)                 # URL de la miniatura de mayor resolución
_preparar_portada(info)                # recorta a 1:1 y escala a 1200x1200 JPEG (FFmpeg)
_escribir_metadatos(filepath, titulo, portada)  # ©ART/©nam + carátula covr en el .m4a
_procesar_descarga(task_id)            # descarga UNA tarea y actualiza su estado
_marcar_procesando(task_id, datos)     # pasa a "procesando" con la etapa del postprocesador
_worker_descargas()                    # hilo único: saca tareas de cola_descargas y las procesa
_asegurar_worker()                     # arranca el worker una sola vez (_worker_lock)
_guardar_historial()                   # persiste las tareas en %APPDATA%\DownloaderMusic\historial.json
_cargar_historial()                    # las recupera al arrancar (interrumpidas → error)
```

**Flujo del worker (importante al editar):**

1. `_worker_descargas` espera en `cola_descargas.get()` y procesa **una tarea a la vez**.
2. `_procesar_descarga` marca la tarea `descargando` y llama a `descargar_audio_con_progreso`.
3. El `progreso_hook` actualiza `porcentaje/descargado/total/eta/speed` mientras descarga bytes.
   yt-dlp solo lo llama **una vez por bloque** (los bloques crecen hasta 4 MB), así que el primer
   aviso arranca `_muestrear_progreso`: un hilo que lee el tamaño real del `.part` cada 0,1 s y
   escribe %/velocidad/ETA (media móvil). Termina solo cuando la tarea deja de estar `descargando`.
4. Al recibir `status == "finished"` la tarea pasa a **`procesando`** (100 %): ya no descarga,
   ahora yt-dlp convierte/etiqueta. El `postproceso_hook` va cambiando `etapa`
   (`Convirtiendo a M4A…`, `Escribiendo metadatos…`, `Incrustando carátula…`).
5. **Regla del nombre** (`_componer_nombre`): si el título no trae `"-"`, se antepone
   `"Autor - "` usando el `uploader` (quitando el sufijo `" - Topic"`); si ya trae guion se
   respeta. Los `"#"` iniciales se limpian (`"## Canción"` → `"Canción"`).
6. `_preparar_portada` descarga la miniatura más grande, la recorta centrada a **1:1** y la escala
   a **1200×1200** JPEG (etapa "Preparando portada 1:1…"). Requiere FFmpeg en PATH.
7. `_escribir_metadatos` escribe `©ART`/`©nam` y la carátula `covr` (si algo falla, solo avisa:
   la descarga sigue válida). La división `artista - título` se hace en el **primer** guion.
7. Éxito → estado `descargado` al 100 % (archivo ya disponible en la carpeta del usuario);
   fallo → estado `error` con mensaje limpio (sin ANSI).
8. La tarea **no se borra nunca**: el historial vive en memoria hasta cerrar la app.

> ⚠️ **El "renombrado" NO cambia el nombre del archivo en disco**: solo escribe metadatos.
> El archivo queda con el título del video de YouTube (plantilla `%(title)s.%(ext)s`).

**Opciones de yt-dlp marcadas 🔥 CLAVE (no tocar sin entender su motivo):**

| Opción | Valor | Por qué está |
|--------|-------|--------------|
| `format` | `"bestaudio"` | Descargar solo audio |
| `outtmpl` | `DOWNLOAD_DIR/%(title)s.%(ext)s` | Guardar en Descargas con el título del video |
| `quiet` | `True` | Sin ruido en consola |
| `noplaylist` | `True` | Un video = una descarga |
| `progress_hooks` | `[progreso_hook]` | Alimenta la barra de progreso del frontend |
| `cookiefile` | `"cookies.txt"` | 🚨 Cookies de YouTube (ruta **relativa al cwd**) |
| ~~`writethumbnail`~~ | — | **Eliminado**: la portada se prepara a mano con `_preparar_portada` |
| `js_runtimes.node.executable_path` | `C:\Program Files\nodejs\node.exe` | 🔥 **Ruta FIJA**. Necesario para resolver el desafío JS de YouTube |
| `remote_components` | `["ejs:github"]` | 🔥 Descarga el solver EJS de GitHub (arregla el **403**) |
| `http_headers.User-Agent` | UA de Android YouTube 17.31.35 | 🔥 Anti-bloqueo |
| `postprocessors[0]` | `FFmpegExtractAudio` → `m4a` | Convertir a `.m4a` (requiere FFmpeg en PATH) |
| `postprocessors[1]` | `FFmpegMetadata` | Metadatos del contenedor |
| ~~`postprocessors[2]`~~ | ~~`EmbedThumbnail`~~ | **Eliminado**: incrustaba la miniatura 16:9; ahora la carátula 1:1 la pone `_preparar_portada` + mutagen |

**Notas al final del archivo:** comandos de mantenimiento (actualizar yt-dlp, pip, etc.). Son
comentarios de referencia; no ejecutarlos automáticamente.

---

### 4.2 [launcher.py](./launcher.py) — Entrada del .exe

- Lanza Flask en un **hilo daemon** (`127.0.0.1:5000`, `debug=False`, `use_reloader=False`).
  - `use_reloader=False` es **obligatorio**: el reloader duplicaría procesos y pywebview abriría
    dos ventanas.
- Espera 1 s (dar tiempo a Flask a arrancar).
- Abre la ventana `webview.create_window("Descargador de Música", ..., 900x600, resizable=True)`.
- `webview.start(icon=ruta_icono())` bloquea hasta cerrar la ventana. `ruta_icono()` devuelve
  `Downloader-ico.ico` desde la carpeta del script o desde `sys._MEIPASS` (spec lo incluye en
  `datas`); si no existe, pywebview usa el icono del `.exe`.

> No usa `webbrowser`: la app es de escritorio, no navegador.

---

### 4.3 [updater.py](./updater.py) — Actualizador externo

**Qué es:** programa independiente que se compila a `updater.exe` ([updater.spec](./updater.spec))
y que la app copia y ejecuta **cuando la nueva versión ya está descargada**. No descarga nada:
de la descarga se encarga la app (con barra de progreso, ver §6).

**Parámetros (sys.argv):**

| Posición | Contenido | Ejemplo |
|----------|-----------|---------|
| `argv[1]` | Ruta del `.exe` **nuevo** ya descargado | `%TEMP%\DownloaderMusicUpdate\nueva_version.exe` |
| `argv[2]` | Ruta del `.exe` actual a reemplazar | `C:\...\Downloader Music Youtube v1.1.5.exe` |

**Flujo:**

1. Valida que existan el archivo nuevo y el actual.
2. Comprueba que el nuevo empiece por `MZ` (es un `.exe` de Windows).
3. `os.replace(nuevo, actual)` reintentando cada 0.5 s (hasta 60 s) mientras Windows tenga
   bloqueado el exe porque la app aún se está cerrando.
4. Relanza la app actualizada y termina.
5. Si algo falla: `MessageBoxW` con el error (el updater va con `console=False`, no tiene consola),
   escribe `%TEMP%\DownloaderMusicUpdate\updater.log` y vuelve a abrir la app anterior.

---

### 4.4 [version.py](./version.py) y [version.json](./version.json)

- `version.py`: `VERSION = "0.0.0"` → versión de desarrollo. La usan `/version` y el badge.
  **Antes de compilar una release hay que subirla** (p. ej. `1.0.1`): el número va dentro del
  `.exe` y es lo que se compara con GitHub.
- **Guarda de desarrollo:** solo `VERSION = "0.0.0"` desactiva la búsqueda de actualizaciones (para
  no molestar en pruebas). Cualquier build publicada (0.0.1, 0.0.2, 1.0.0…) sí consulta GitHub.
- `version.json` (rama `main`) es el **respaldo** si la API de GitHub falla: debe tener
  `version`, `url` (descarga directa del asset, `/releases/download/<tag>/<archivo>.exe`) y
  `mensaje`. Con la API funcionando no hace falta tocarlo.
- La versión que manda es la **Release**: se toma la mayor entre el `tag_name` y el `name`
  (GitHub permite tag y título distintos; el repo llegó a tener tag `v1.0.5` con título `v1.1.5`).

---

### 4.5 [templates/index.html](./templates/index.html) — Interfaz activa

- Bootstrap 5.3.3 por CDN (necesita internet; si no hay red, la UI pierde estilos).
- Carga su propio CSS `static/css/descargas.css` (panel de descargas: scroll fino, textos y
  animaciones). El resto de `static/css/` no se usa (ver §4.7).
- **Iconos e instalación como web app:** `<link rel="icon">` usa `static/iconos/icon-32.png`
  (32×32) e `icon-192.png`; `apple-touch-icon` usa `icon-180.png`; `manifest.json` declara los
  iconos 192/512 y el maskable para **Android/iPhone** (Añadir a pantalla de inicio), con
  `theme-color` `#198754`. Todos salen de `static/Downloader-ico.png` (ver §4.7).
- Estructura de dos columnas **9/3** (el gestor de descargas es la mitad de ancho que antes):
  - **Izquierda (formulario + vista previa, `col-md-9`):** input `#youtube-url`, `.Btn-Pegar`,
    `.Btn-Buscar-Cancion`, `.loading` (spinner) y `#Informacion-Cancion` (oculta con `d-none`
    hasta buscar). La vista previa es **vertical**: imagen arriba (`.Imagen-Caratula`) y debajo
    título, duración/autor, `#rename-title` (con icono de ayuda **ⓘ** que abre un popover con la
    regla `Autor - Título`) y `.Btn-Descargar-Cancion` (**"Descargar"**). La carátula se muestra
    **1:1** (160×160, `object-fit: cover`).
  - **Derecha (gestor de descargas, `col-md-3`):** encabezado con `#Contador-Descargas`, radios
    `#vista-detallada` / `#vista-compacta` (`name="vista-descargas"`), lista scrollable
    `#Lista-Descargas` y estado vacío `#Descargas-Vacias`.
- Navbar: botón `#btn-abrir-carpeta` (📁, abre `Downloads\DownloaderMusic`) + badge
  `#version-app` (lo rellena JS con `v0.0.0`).
- `#Aviso-Cola` está **fuera** de la vista previa para que siga visible cuando el formulario se
  limpia tras encolar.
- Modal `#modalActualizacion`: `#version-nueva`, `#mensaje-actualizacion` (notas con scroll),
  `#btn-actualizar`, barra `#progreso-actualizacion`/`#barra-actualizacion` y texto
  `#estado-actualizacion` (progreso de la descarga).
- Carga `static/js/script.js` al final.

> ⚠️ **Los nombres de clases/IDs son el contrato con `script.js`.** Si se cambia un selector en
> el HTML hay que cambiarlo también en el JS (`querySelector`), o la interfaz deja de responder.

---

### 4.6 [static/js/script.js](./static/js/script.js) — Lógica del cliente

**Estructura:** todo dentro de `DOMContentLoaded` para garantizar que existan los nodos.

**Selectores que deben coincidir con `index.html`:**

```text
.Btn-Buscar-Cancion, .Btn-Pegar, #youtube-url, .loading, #Informacion-Cancion,
.Titulo-Cancion, .Informacion-Cancion-p, .Imagen-Caratula, #rename-title,
.Btn-Descargar-Cancion, #Aviso-Cola, #Lista-Descargas, #Descargas-Vacias,
#Contador-Descargas, #btn-abrir-carpeta, input[name="vista-descargas"]
```

**Funciones y flujo:**

| Función | Qué hace |
|---------|----------|
| `obtenerInfo(url)` | `POST /informacion`; si `!res.ok` lanza el JSON de error |
| `mostrarPreview(videoInfo)` | Rellena título, duración `h:mm:ss`, autor y miniatura; calcula el nombre con `nombrePropuesto()`, habilita inputs y quita `d-none` a la vista previa |
| `limpiarNombre(texto)` | Quita caracteres inválidos de Windows (`[<>:"/\|?*]`), `"#"` iniciales y espacios |
| `nombrePropuesto(videoInfo)` | **Regla**: si el título no tiene guion → `"Autor - Título"` (sin sufijo `" - Topic"`); si ya tiene guion → se respeta tal cual |
| `encolarDescarga(url, customTitle, uploader)` | `POST /descargar` → la tarea queda `En cola`; envía también el autor como respaldo |
| `actualizarDescargas(forzar)` | `GET /descargas` y renderiza. Sondeo **adaptativo**: 100 ms con algo en curso y 800 ms en reposo (se reprograma sola). Con la lista sin cambios solo refresca %/velocidad/ETA en sitio |
| `renderizarDescargas(datos)` | Pinta 3 grupos: **En curso**, **En cola**, **Historial**; actualiza `#Contador-Descargas`, el estado vacío y detecta con `estadosPrevios` las tareas que acaban de pasar a `descargado` para animarlas |
| `crearItemDescarga(tarea, completadaAhora)` | Construye cada tarjeta con `createElement` + `textContent` (sin `innerHTML` → evita inyección). Vista **detallada**: `.Descarga-Cabecera` (nombre + ×) y `.Descarga-Badge` centrado debajo; vista **compacta**: solo nombre + icono. Si `completadaAhora` añade `.Descarga-Completada` (destello verde) |
| `crearIconoEstado(tarea)` | Icono de la vista compacta: `✔` verde (`descargado`), `✖` rojo (`error`), `%` mientras descarga y `#N` en cola |
| `crearBotonEliminar(tarea)` | Botón **×** de cada tarea terminada → `quitarDelHistorial()` |
| `quitarDelHistorial(taskId)` | `DELETE /descargas/<id>`: quita la entrada del historial (no borra el archivo) y repinta |
| `limpiarHistorial()` | `DELETE /historial` con `confirm()`: vacía el historial (no borra archivos) |
| `aplicarVista(valor)` / `restaurarVista()` | Cambian entre vista `detallada` y `compacta`, repintan y guardan la elección en `localStorage("vistaDescargas")` |
| `animarDescargaCompletada(item)` | Clona el badge (o el icono en vista compacta) como `.Descarga-Volando`, `position: fixed`, y lo vuela con la Web Animations API hasta `#btn-abrir-carpeta` (curva hacia arriba, 750 ms); al aterrizar pulsa el botón |
| `pulsarCarpeta()` | Reinicia la animación `.Carpeta-Pulso` del botón 📁 (latido + halo verde) |
| `textoEstado` / `claseBadge` / `claseBarra` / `detalleIzquierda` / `detalleDerecha` | Traducen el estado del backend a texto, color de badge/barra y detalles (`%`, etapa, velocidad, ETA, posición en cola, hora) |
| `formatearBytes` / `formatearEta` / `formatearHora` / `formatearDuracion` | Formato legible de tamaños, tiempos y duración (`formatearHora` en 12 h: `10:41 AM`) |
| `toggleLoading(show)` / `mostrarAviso(texto)` | Spinner de búsqueda y aviso "Añadido a la cola ✔" (2,5 s) |
| `limpiarFormulario()` | Tras encolar: vacía URL y nombre, deshabilita campos, oculta la vista previa y enfoca el input |
| `cargarVersion()` | `GET /version` → badge `v0.0.0` |
| `cargarCarpeta()` + click en `#btn-abrir-carpeta` | `GET /carpeta` (tooltip con la ruta) y `POST /abrir-carpeta` (abre el Explorador) |
| `compararVersiones(a, b)` | Compara versiones por tramos numéricos (`v1.0.1`, `1.0.1-beta`…); `true` si la remota es mayor |
| `comprobarActualizacion()` | `GET /actualizacion`; si la Release es mayor muestra el modal (una vez por sesión) |
| `iniciarActualizacion(datos)` | `POST /actualizar` y arranca `vigilarActualizacion()` |
| `vigilarActualizacion()` | `GET /actualizar/progreso` cada 300 ms: barra, MB descargados y "Reiniciando…" al quedar `lista` |

**Estados que devuelve el backend y cómo se pintan:**

| `estado` | Badge | Barra | Detalle |
|----------|-------|-------|---------|
| `cola` | `En cola` (gris) | 0 % | `#N en cola` con su posición |
| `descargando` | `Descargando X%` (verde) | verde, % real | `X% · velocidad/s · ETA m:ss` + `descargado / total` |
| `procesando` | `Procesando` (amarillo) | amarilla **rayada animada** al 100 % | `etapa` del backend (`Convirtiendo a M4A…`, etc.) |
| `descargado` | `Descargado ✔` (verde) | 100 % | `100% · nombre_archivo` + hora de fin |
| `error` | `Error` (rojo) | 0 % | mensaje del error (sin ANSI) + hora de fin |

**Puntos delicados del JS:**

- El sondeo a `/descargas` es **adaptativo** (`setTimeout` encadenado): **100 ms** mientras hay
  tareas en `activas`/`cola` y **800 ms** en reposo. Así cualquier ventana ve las descargas
  iniciadas en otra y la barra se mueve fluida sin castigar la CPU cuando no hay nada activo.
  Para que 10 sondeos/s no repinten la lista entera, `firmaEstructuraDe()` compara ids/estados y,
  si la estructura no cambió, `actualizarTareasEnCurso()` actualiza solo badge, barra y detalles
  (sin destruir nodos: los clics en × no se pierden). `peticionActual` descarta respuestas viejas.
- Los nombres se insertan con `textContent`, nunca con `innerHTML`: los títulos vienen de YouTube.
- `ImagenVacia = "/static/sinimagen.png"` y `imagen.onerror` se anula tras el primer fallo
  (evita bucles de carga). Ver §11.6.
- El botón "Descargar" envía `input.value.trim()` como URL y `renameInput` como título; si la
  petición falla deja todo como estaba, y si va bien llama a `limpiarFormulario()`.
- El icono **ⓘ** (`#btn-regla-nombre`) abre un **popover de Bootstrap** con `trigger: "manual"`,
  una **X** (`.regla-cerrar`) en la esquina y cierre al **pulsar fuera** del recuadro. El contenido
  es fijo del código, por eso usa `sanitize: false` y `container: "body"`. Se protege con
  `if (window.bootstrap)` por si el CDN no carga. La regla también se aplica en el backend
  (`_componer_nombre`).
- Cada tarjeta tiene cabecera propia (`.Descarga-Cabecera`): el nombre ocupa el ancho disponible
  y la **×** queda a la derecha. El badge va debajo **centrado vertical y horizontal**
  (`.Descarga-Estado` + `.Descarga-Badge`), que es lo que queda bien en el panel estrecho
  (`col-md-3`).
- **Vista compacta** (radios `Detallada` / `Compacta`): muestra solo `Autor - Título` + icono
  (`✔` / `✖` / `%` / `#N`), sin barra ni detalle, para listas largas. La elección se guarda en
  `localStorage`; `crearItemDescarga()` consulta `vistaCompacta`.
- **Historial:** la **×** de cada tarea terminada y "Limpiar todo" llaman a `DELETE` en el
  backend, que solo borra el registro visual (los `.m4a` siguen en `Downloads\DownloaderMusic`).
  Las tareas en curso no se pueden quitar (409). `formatearHora()` usa formato de **12 horas**
  (`10:41 AM`).
- **Animación de fin de descarga (tipo Chrome):** se dispara solo con la transición a
  `descargado` que ve el sondeo (`estadosPrevios`); el historial cargado al abrir la app **no**
  se anima. El clon vuela en `<body>` porque la lista se repinta al cambiar la estructura (no en
  cada sondeo). Se respeta `prefers-reduced-motion` (con movimiento reducido no hay vuelo).
- `navigator.clipboard.readText()` puede fallar según permisos/contexto (por eso el try/catch).
- El usuario puede encolar varias canciones seguidas: no hay que esperar a que termine ninguna.

---

### 4.7 `static/css/*` — Un archivo activo y el resto histórico

- `descargas.css`: **ACTIVO** (lo carga `index.html`): scroll fino verde de `#Lista-Descargas`,
  tipografía de las tarjetas (`.Descarga-Nombre`, `.Descarga-Badge`, `.Descarga-Detalle`),
  radios de vista, botón × (`.Descarga-Eliminar`), "Limpiar todo" (`.Descarga-Limpiar`) y
  animaciones de fin de descarga (`.Descarga-Completada`, `.Descarga-Volando`, `.Carpeta-Pulso`).
- `iconos/` + `manifest.json`: iconos de la web app (32, 180, 192, 512 y maskable 512) y el
  manifest para instalarla en Android/iPhone. `Downloader-ico.png` es el original.
- `style.css`: reset, fondo, estilos del diseño antiguo (clases `.Titulo`, `.url-input`, etc.).
- `previews.css`: estilos del preview antiguo; contiene `#Informacion-Cancion { display: none; }`.
- Los dos `*-resposive.css`: media queries del diseño antiguo (el nombre tiene la errata
  "resposive" y así se quedó).

> ⚠️ Los CSS históricos **no están enlazados** en `index.html`. Si se enlazan sin revisar,
> `previews.css` ocultaría el panel derecho (`display: none`) y rompería la UI actual.

---

## 5. Flujo de ejecución

### 5.1 Desarrollo (`python app.py`)

```text
python app.py  →  Flask en 0.0.0.0:5000 con debug=True
              →  Abrir manualmente http://127.0.0.1:5000 en el navegador
```

> `host="0.0.0.0"` + `debug=True` solo para desarrollo: expone la app a la red local y activa el
> depurador interactivo de Werkzeug. **No usar así en producción.**

### 5.2 Producción (`.exe`)

```text
Downloader Music Youtube v1.1.5.exe
   └─ launcher.py (congelado)
        ├─ hilo: Flask en 127.0.0.1:5000 (debug=False, sin reloader)
        └─ ventana pywebview → http://127.0.0.1:5000
```

### 5.3 Secuencia de una descarga (con cola)

```text
[Cliente]                                [Flask]                        [worker / yt-dlp]
   │ POST /informacion {url} ────────────▶ obtener_info(download=False)
   │ ◀────────────── {title, duration, thumbnail, uploader}
   │ (pinta vista previa, rellena #rename-title)
   │ POST /descargar {url, custom_title} ─▶ registra tarea "cola" + cola_descargas.put()
   │ ◀────────────── {task_id}            (responde AL INSTANTE, sin descargar aún)
   │ cada 100 ms (0,8 s en reposo) GET /descargas ─▶ lee el registro (con candado)
   │ ◀────────────── {activas, cola, historial}
   │                                       └─ worker: saca la 1ª tarea → "descargando" (bytes + %)
   │                                          → "procesando" (Convirtiendo a M4A…, metadatos,
   │                                             carátula; barra rayada al 100 %)
   │                                          → "descargado" en ~/Downloads/DownloaderMusic
   │ (el formulario se limpia al encolar y se pueden añadir más: "En cola #1, #2…")
   │ el sondeo es adaptativo: cualquier ventana refleja la cola y el historial (0,1 s / 0,8 s)
```

---

## 6. Versionado y actualización automática

```text
version.py (local) ──▶ /version ──▶ badge "v1.1.5" en la UI
GitHub Releases (latest) ──▶ /actualizacion ──▶ compara versiones en JS
                                                    │
                                        ¿remota > local? ── no ──▶ fin
                                                    │ sí
                                                    ▼
                              modal "Nueva actualización" (versión + notas)
                                                    │ clic "Actualizar"
                                                    ▼
                    POST /actualizar (solo si sys.frozen)
                    descarga el asset de la Release en %TEMP% con barra de progreso
                    (GET /actualizar/progreso cada 300 ms)
                                                    ▼
                    al terminar: copia updater.exe de _MEIPASS, lo lanza
                    updater.exe <nueva_version.exe> <exe_actual> y os._exit(0)
                                                    ▼
                    updater.exe: os.replace con reintentos → relanza la app nueva
```

**Checklist al publicar una versión nueva:**

1. Sube `VERSION` en [version.py](./version.py) (p. ej. `1.0.1`) **antes de compilar**: el número
   va dentro del `.exe` y es el que se compara con GitHub.
2. Compila primero `updater.exe` y después la app (ver §7).
3. Crea la Release en GitHub con un tag **mayor** que la versión instalada (recomendado `v1.0.1`,
   igual que `VERSION`) y adjunta el `.exe` compilado como asset.
4. (Opcional) actualiza [version.json](./version.json) como respaldo si la API fallara.

Las instalaciones anteriores comprueban la Release al arrancar, muestran el modal y, con un clic,
descargan e instalan la nueva versión sin pasos manuales.

---

## 7. Empaquetado (PyInstaller)

| Spec | Script | Incluye | Estado |
|------|--------|---------|--------|
| [Downloader Music Youtube v1.1.5.spec](./Downloader%20Music%20Youtube%20v1.1.5.spec) | `launcher.py` | `templates/`, `static/`, icono `Downloader-ico.ico`, `dist/updater.exe`, `console=False` | ✅ **Vigente** |
| [build.spec](./build.spec) | `launcher.py` | `webview` completo (`collect_all`), `templates/`, `static/`, `cookies.txt` | ⚠️ Alternativo/antiguo (`console=True`) |
| [updater.spec](./updater.spec) | `updater.py` | Nada extra | ✅ Vigente para `updater.exe` |
| Resto de `.spec` en raíz | varias | — | 📦 Historial, no usar |

**Comandos (en este orden):**

```powershell
# 1) Compilar el actualizador (el spec de la app lo incrusta desde dist\updater.exe)
.\.venv\Scripts\python.exe -m PyInstaller updater.spec --noconfirm

# 2) Compilar la app (spec vigente)
.\.venv\Scripts\python.exe -m PyInstaller "Downloader Music Youtube v1.1.5.spec" --noconfirm

# Resultado: dist\updater.exe y dist\Downloader Music Youtube v1.1.5.exe
```

> ⚠️ El spec vigente incluye `('dist/updater.exe', '.')` en `datas`, así que **hay que compilar
> `updater.exe` primero** (si no existe, PyInstaller falla). Verificado: el exe de la app contiene
> `updater.exe` en la raíz de `sys._MEIPASS`.
>
> ⚠️ `cookies.txt` **no** está en el spec v1.1.5 (sí en `build.spec`). Si yt-dlp necesita
> cookies, el `.exe` debe encontrarlas en el **directorio de trabajo** (por eso `dist\cookies.txt`
> existe). Ver §11.3.

---

## 8. Recursos y archivos binarios

| Archivo | Uso |
|---------|-----|
| [icono.ico](./icono.ico) | Icono del ejecutable (`icon=` del spec) |
| [icono.png](./icono.png) | Favicon de la página (`url_for('static', filename='icono.png')`) ❗ Está en la **raíz**, no en `static/` |
| [sinimagen.png](./static/sinimagen.png) | Placeholder de carátula |
| [downloader.png](./downloader.png) | Referenciado por JS como fallback, pero en ruta no servida |
| `node/node-v20.11.0-win-x64/` | Node portable versionado (no usado por el código) |

> ❗ Ojo: `index.html` pide `static/icono.png`, pero el archivo `icono.png` está en la raíz del
> proyecto (no dentro de `static/`). El favicon probablemente da 404. Está documentado, no
> corregido (§11.8).

---

## 9. Git y control de versiones

- Rama activa: `main`. Árbol de trabajo limpio al redactar este documento.
- Últimos commits relevantes: "Nueva actualizacion", "lo que Dios quiera",
  "Actualizacion de datos y bugs arreglados", documentación y renombrado de variables.
- **Se versionan** `build/`, `dist/`, `node/`, `__pycache__/` y `cookies.txt` (≈2354 archivos).
  Esto hace el repo pesado y expone artefactos.
- **No existe `.gitignore`.**

---

## 10. Cómo ejecutar y mantener

```powershell
# Ejecutar en desarrollo (SIEMPRE con el venv, porque el Python global no tiene yt-dlp)
.\.venv\Scripts\python.exe app.py
# Abrir http://127.0.0.1:5000

# Ejecutar con ventana nativa (como el .exe)
.\.venv\Scripts\python.exe launcher.py

# Actualizar yt-dlp (YouTube cambia seguido; esto es mantenimiento habitual)
.\.venv\Scripts\python.exe -m pip install -U yt-dlp

# Ver versión instalada de yt-dlp
.\.venv\Scripts\python.exe -m yt_dlp --version
```

> Si YouTube empieza a dar errores 403/400 de nuevo, el orden de revisión es:
> 1) actualizar `yt-dlp`, 2) comprobar que Node sigue en `C:\Program Files\nodejs\node.exe`,
> 3) comprobar que `cookies.txt` es válido y no está caducado, 4) comprobar FFmpeg en PATH.

---

## 11. ⚠️ Puntos delicados al editar (checklist)

### 11.1 🚨 `cookies.txt` está versionado y el repositorio es PÚBLICO

`cookies.txt` contiene cookies de sesión de YouTube y **está subido a GitHub en un repo público**
(confirmado: aparece en la raíz del repo remoto). Cualquiera puede usarlas.

**Qué hacer (cuando el usuario lo autorice):**

1. Cerrar sesión / revocar las sesiones de YouTube asociadas y regenerar las cookies.
2. `git rm --cached cookies.txt` y añadir `cookies.txt` a un `.gitignore`.
3. Limpiar el historial (p. ej. `git filter-repo`) si se quiere eliminar el rastro.
4. Distribuir las cookies solo junto al `.exe` local, nunca en el repo.

> Mientras el archivo siga en el repo, **no** pegarlo en issues, chats ni capturas.

### 11.2 Ruta de Node fija

`app.py` usa `C:\Program Files\nodejs\node.exe` (hoy Node **24.21.0** ahí). Si el usuario final no
tiene Node instalado en esa ruta, la descarga falla. El repo ya trae un Node portable en
`node/node-v20.11.0-win-x64/node.exe`, pero **nadie lo usa**. Cualquier mejora debería resolver la
ruta dinámicamente (PATH, ruta del exe empaquetado) sin romper el arreglo del 403.

### 11.3 `cookies.txt` con ruta relativa

`"cookiefile": "cookies.txt"` depende del **directorio de trabajo**. En el `.exe` de una sola
carpeta (`onefile`), el cwd suele ser la carpeta desde donde se lanza. Si se cambia la forma de
empaquetar o se lanza desde otro directorio, yt-dlp no encontrará las cookies.

### 11.4 `updater.exe` fuera del spec vigente

Ver §7. La auto-actualización requiere que `updater.exe` esté dentro del bundle (`sys._MEIPASS`).

### 11.5 ✅ RESUELTO — Actualización automática

- `/actualizacion` ya no depende de `version.json`: consulta la **API de Releases** y usa la
  mayor versión entre el tag y el nombre de la release (el repo tenía tag `v1.0.5` con título
  `v1.1.5`). `version.json` solo queda como respaldo.
- La descarga la hace la app (con progreso real en el modal); `updater.exe` solo reemplaza y
  reinicia, por lo que ya no parsea URLs ni consulta la API.
- `updater.exe` se incrusta en el bundle vía `datas=[('dist/updater.exe', '.')]` (ver §7).

### 11.6 ✅ RESUELTO — Fallback de imagen

El JS ya usa `ImagenVacia = "/static/sinimagen.png"` (ruta que sí sirve Flask) y desactiva el
`onerror` tras el primer fallo, así que no hay bucle de carga. `downloader.png` quedó sin uso.

### 11.7 CSS legado no enlazado

Ver §4.7. No enlazar `previews.css` sin revisar `#Informacion-Cancion { display:none }`.

### 11.8 `icono.png` fuera de `static/`

`index.html` lo busca en `static/`; el archivo está en la raíz. El favicon no funciona.

### 11.9 Ruta `/download_file` comentada

Si se reactiva, hay que reactivar también:

- `import mimetypes` (está comentado en la cabecera),
- la función `limpiar_archivo` (comentada),
- `send_file` + `after_this_request` + la parte del JS (`a.href`, `a.download`).

Son cuatro piezas que se activan juntas; activar solo una rompe la descarga.

### 11.10 Registro de descargas (cola + historial)

- `descargas` está protegido por `descargas_lock`; siempre leer con `_leer_descarga`/`_listar_descargas`.
- El worker es **único** y procesa en orden: no hay dos yt-dlp compitiendo por la misma sesión.
- `_asegurar_worker()` usa `_worker_lock` para no crear dos workers.
- **El historial persiste en disco** en `%APPDATA%\DownloaderMusic\historial.json`
  (`_guardar_historial` / `_cargar_historial`, máximo `MAX_HISTORIAL = 100` tareas). Se guarda solo
  al **cambiar de estado** (no en cada tick de progreso). Al arrancar, las tareas que quedaron en
  `cola/descargando/procesando` se marcan como `error` ("Se interrumpió al cerrar la aplicación").
- No hay endpoint para limpiar el historial: se puede borrar/editar ese JSON con la app cerrada.
- `/descargas` incluye **`procesando` dentro de `activas`**; si se olvida, la tarea desaparece de la
  interfaz justo durante la conversión (bug corregido el 12/11/2026).
- Al terminar una descarga correctamente **no se resetea** el porcentaje: queda en `100`.
- Estados: `cola → descargando → procesando → descargado | error`. El paso `procesando` viene de
  `progress_hooks` (`status == "finished"`) y de `postprocessor_hooks`; `etapa` guarda el texto
  que se muestra ("Convirtiendo a M4A…", "Incrustando carátula…", etc.).

### 11.11 `app.py` en modo desarrollo

`app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)` es solo para desarrollo.
Sin reloader hay **un solo proceso** (antes el reloader dejaba hijos fantasma y dos instancias se
repartían el historial). Además, al arrancar se comprueba el puerto 5000 y, si ya hay una instancia,
se sale con un aviso: **nunca debe haber dos servidores a la vez**. El `.exe` no pasa por aquí.

### 11.12 `index copy.html` y `apporiginal4.py`

Son respaldos. Flask solo usa `templates/index.html`; Python solo ejecuta lo importado. No
borrarlos ni editarlos pensando que afectan a la app.

### 11.13 Contrato HTML ↔ JS ↔ CSS

Cambiar `id`/`class` en el HTML exige cambiar `script.js`. Los nombres actuales son
descriptivos y con mayúsculas iniciales a propósito (ej. `.Btn-Buscar-Cancion`).

### 11.14 Recursos que dependen de internet

Bootstrap (CDN), miniatura de YouTube, `remote_components` de yt-dlp (GitHub) y `version.json`
(GitHub). Sin internet, la app arranca pero pierde estilos, miniaturas y actualización.

### 11.15 FFmpeg obligatorio

Sin `ffmpeg` en PATH no se puede postprocesar a `.m4a` ni incrustar la miniatura.

---

## 12. Convenciones para futuras ediciones

1. **Comentar todo cambio** indicando el motivo (el proyecto entero sigue ese patrón).
2. **Usar el intérprete de `.venv`** para ejecutar, probar y compilar.
3. **No renombrar** IDs/clases del HTML sin actualizar `script.js`.
4. **No tocar** los bloques marcados `🔥 CLAVE` de yt-dlp sin probar una descarga real.
5. **Probar siempre** una descarga de extremo a extremo después de tocar `app.py`
   (`/informacion` → `/descargar` → `/progreso` → archivo en `~/Downloads`).
6. **No commitear** `cookies.txt`, ni `build/`, `dist/`, `node/`, `__pycache__/`.
7. Al publicar versión: subir `VERSION` en `version.py`, compilar `updater.exe` + app, y crear la
   Release con un tag mayor y el `.exe` como asset (el `version.json` es solo respaldo).
8. Mantener los separadores `# ---- ... ---- #` que dividen secciones en `app.py`.

---

## 13. Glosario rápido

| Término | Significado en este proyecto |
|---------|------------------------------|
| `task_id` | UUID que identifica una descarga |
| `cola_descargas` | `queue.Queue` FIFO con los `task_id` pendientes |
| `descargas` | Registro en memoria con el estado de todas las tareas (cola, activas e historial) |
| Worker | Hilo único (`_worker_descargas`) que procesa la cola de una en una |
| `estado` | `cola` → `descargando` → `procesando` → `descargado` \| `error` |
| `etapa` | Texto de la fase de postprocesado ("Convirtiendo a M4A…") |
| `DOWNLOAD_DIR` | Carpeta de Descargas del usuario (`~/Downloads`) |
| Spec | Archivo de configuración de PyInstaller |
| `sys._MEIPASS` | Carpeta temporal donde el `.exe` onefile extrae sus datos |
| `sys.frozen` | `True` cuando corre dentro del `.exe` compilado |
| EJS / solver | Componente JS que yt-dlp descarga para resolver el desafío de YouTube (arregla 403) |
| Postprocesador | Paso de yt-dlp que convierte/embebe metadatos después de descargar |
