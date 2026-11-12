# 🎵 YouTube Music Downloader

Aplicación de escritorio para Windows que descarga el audio de YouTube en **`.m4a`** con carátula
1:1 y metadatos, con cola de descargas, historial, progreso en tiempo real y
**actualización automática** desde GitHub Releases.

> Uso personal. No está afiliada a YouTube/Google. Respeta los derechos de autor y los Términos
> de Servicio de YouTube. Los detalles están en el modal **Términos y condiciones** de la app.

---

## ✨ Características

- **Vista previa** del vídeo: título, duración, autor y miniatura.
- **Cola de descargas**: añade varias canciones sin esperar a que termine la anterior.
- **Historial persistente** con el estado real de cada descarga, hora en formato 12 h, vista
  detallada o compacta, quitar una entrada (×) y limpiar todo con confirmación.
- **Progreso fluido** (actualización cada 0,1 s) y animación al terminar que vuela hasta el botón
  de la carpeta.
- **Regla del nombre**: si el título no trae guion se autocompleta como `Autor - Título`; si ya
  trae guion se respeta. El icono **ⓘ** explica la regla.
- **Carátula 1:1 de 1200×1200** incrustada en el `.m4a` (óptima para Apple Music/iPhone).
- **Auto-actualización** desde GitHub Releases: aviso, descarga con barra de progreso,
  reemplazo del `.exe` y reinicio automático.
- **Términos y condiciones** y **apartado de versiones (parches)** con fecha y hora.
- **Iconos** en la pestaña, en la app de escritorio y al añadir a la pantalla de inicio
  (Android/iPhone) mediante `manifest.json`.
- **Paquete portable**: no necesita instalar Python ni librerías.
- Las canciones se guardan en `Descargas\DownloaderMusic` (la carpeta se crea sola).

---

## 🖥 Para usuarios

### Opción A — Instalador (recomendado)

1. Descarga `Instalador YouTube Music Downloader v<versión>.exe` desde
   [Releases](https://github.com/EdgardSk8/Downloader-Music-Youtube/releases).
2. Siguiente → Siguiente → Instalar. Se instala **solo para tu usuario**, **sin permisos de
   administrador**, en `%LOCALAPPDATA%\Programs\YouTube Music Downloader`.
3. Crea accesos directos en el **Escritorio** y el **menú Inicio**, y un **desinstalador**.

### Opción B — Portable

1. Descarga el ZIP portable y descomprímelo donde quieras.
2. Doble clic en `Downloader Music Youtube v<versión>.exe`.

**En ambos casos no hay que instalar Python, FFmpeg ni Node**: van incluidos.

Contenido del paquete:

| Archivo | Para qué |
|---------|----------|
| `Downloader Music Youtube v<versión>.exe` | La app (Python + Flask/yt-dlp/mutagen/pywebview dentro) |
| `ffmpeg.exe` / `ffprobe.exe` | Conversión a M4A, metadatos y portada |
| `node\node.exe` | Reto JS de YouTube |
| `LEEME.txt` | Instrucciones |

- **No hace falta instalar Python, FFmpeg ni Node**: la app busca las herramientas **junto al
  `.exe`** y funciona desde cualquier carpeta.
- La actualización automática reemplaza **solo el `.exe`**; `ffmpeg`, `ffprobe` y `node` se
  conservan.
- Si YouTube pide cookies, coloca tu propio `cookies.txt` junto al `.exe` (no lo compartas).
- Requisitos: **Windows 10/11 de 64 bits** y **WebView2** (viene preinstalado en la mayoría).
- El `.exe` no está firmado digitalmente: SmartScreen puede pedir confirmación la primera vez.

---

## 🐧 Linux (interfaz en el navegador)

En Linux la app **no abre ventana nativa**: arranca el servidor y abre la interfaz en tu
**navegador** por defecto (`http://127.0.0.1:5000`). El resto de funciones es idéntico (cola,
historial, progreso, actualización automática, etc.).

### Opción A — Binario (recomendado)

1. Descarga `Downloader.Music.Youtube.v<versión>.linux-x86_64` desde
   [Releases](https://github.com/EdgardSk8/Downloader-Music-Youtube/releases) (va junto al `.exe`
   de Windows) y guárdalo en tu carpeta personal, p. ej. `~/Apps`.

   ```bash
   mkdir -p ~/Apps && mv Downloader.Music.Youtube.v*.linux-x86_64 ~/Apps/
   ```

2. Requisitos del sistema (una sola vez): `sudo apt install ffmpeg nodejs`
   (Fedora: `sudo dnf install ffmpeg nodejs` · Arch: `sudo pacman -S ffmpeg nodejs`).

3. Permiso de ejecución y arranque:

   ```bash
   chmod +x ~/Apps/Downloader.Music.Youtube.v*.linux-x86_64
   ~/Apps/Downloader.Music.Youtube.v*.linux-x86_64
   ```

4. Se abre el navegador. **Deja la terminal abierta** (si la cierras, la app se cierra);
   `Ctrl+C` para salir. Si el navegador no se abre, entra a `http://127.0.0.1:5000`.

5. Datos: canciones en `~/Downloads/DownloaderMusic`, historial en
   `~/.config/DownloaderMusic/historial.json`. `cookies.txt` es opcional y va junto al binario.

> Guárdalo en una carpeta donde puedas escribir: la actualización automática reemplaza el propio
> binario (no funciona en rutas de solo lectura como `/opt`).

Los mismos pasos van en [LEEME-Linux.txt](./LEEME-Linux.txt), que se publica junto al binario.

### Opción B — Desde el código / compilar

Desde el código:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install Flask yt-dlp mutagen
python3 launcher_linux.py
# Se abre el navegador. Ctrl+C en la terminal para salir.
```

Compilar el binario (en Linux; PyInstaller **no** compila cruzado):

```bash
chmod +x build-linux.sh
./build-linux.sh
# Resultado: dist/Downloader Music Youtube v<versión>  (+ icono y .desktop)
```

Si no tienes Linux, usa el workflow incluido: en GitHub → **Actions → “Compilar binario Linux”
→ Run workflow**. Al terminar, descarga el artifact `Downloader-Music-Youtube-linux-x86_64`
(binario + `LEEME-Linux.txt`) y adjúntalo a la Release; si subes un tag `vX.Y.Z`, el workflow lo
adjunta solo.

Para publicarlo como asset de Linux, renómbralo a
`Downloader.Music.Youtube.v<versión>.linux-x86_64`: la app elige el asset según su plataforma.

---

## 🛠 Desarrollo

Requisitos: **Python 3.14.7**, **FFmpeg**, **Node.js** (o el portable de `node/`).

```powershell
# Dependencias
.\.venv\Scripts\python.exe -m pip install Flask yt-dlp mutagen pywebview

# Ejecutar en desarrollo
.\.venv\Scripts\python.exe app.py
# Abrir http://127.0.0.1:5000
```

### Compilar el `.exe`

```powershell
# 1) Dependencias al día (yt-dlp cambia a menudo)
.\.venv\Scripts\python.exe -m pip install -U yt-dlp Flask mutagen pywebview

# 2) Subir VERSION en version.py y añadir la entrada corta en PARCHES (static/js/script.js)

# 3) Compilar PRIMERO el actualizador y DESPUÉS la app
.\.venv\Scripts\python.exe -m PyInstaller updater.spec --noconfirm
.\.venv\Scripts\python.exe -m PyInstaller "Downloader Music Youtube v1.1.5.spec" --noconfirm

# Resultado: dist\Downloader Music Youtube v<VERSION>.exe (el nombre sale de version.py)

# 4) Instalador (opcional, requiere Inno Setup: winget install JRSoftware.InnoSetup)
.\build-installer.ps1
# Resultado: dist\Instalador YouTube Music Downloader v<VERSION>.exe
```

### Publicar una versión

1. Sube `VERSION` en [`version.py`](./version.py) (p. ej. `0.0.4`).
2. Añade una entrada corta al array `PARCHES` de [`static/js/script.js`](./static/js/script.js).
3. Compila (ver arriba).
4. Crea una **Release** en GitHub con un tag mayor (p. ej. `v0.0.4`) y adjunta el `.exe`.
5. Opcional: actualiza [`version.json`](./version.json) como respaldo.

Las instalaciones anteriores detectan la nueva versión al arrancar y se actualizan solas.

> Para el paquete portable: copia el `.exe`, `ffmpeg.exe`, `ffprobe.exe` y `node\node.exe` en una
> carpeta y comprímela. Ver [ESTRUCTURA.md](./ESTRUCTURA.md) §7.1.

---

## 📁 Estructura

| Ruta | Qué es |
|------|--------|
| `app.py` | Flask + yt-dlp + metadatos + endpoints |
| `launcher.py` | Entrada del `.exe` (Flask en un hilo + ventana pywebview) |
| `launcher_linux.py` | Entrada en Linux (Flask + navegador, sin GTK/WebKit) |
| `build-linux.sh` | Compila el binario Linux (updater + app) |
| `.github/workflows/build-linux.yml` | CI que compila el binario Linux y lo adjunta a la Release |
| `LEEME-Linux.txt` | Instrucciones para el usuario de Linux (se publica con el binario) |
| `updater.py` | Reemplaza el `.exe` y reinicia la app |
| `templates/index.html` | Interfaz (Bootstrap 5) |
| `static/js/script.js` | Lógica del cliente |
| `static/css/descargas.css` | Panel de descargas, modales y animaciones |
| `static/iconos/`, `static/manifest.json` | Iconos y PWA |
| `version.py` / `version.json` | Versión local y respaldo de actualización |
| `ESTRUCTURA.md` | Documentación técnica detallada |

---

## ⚖️ Aviso legal

Herramienta personal y sin ánimo comercial. El usuario es el único responsable del uso que haga
de ella y del contenido que descargue. No aloja ni distribuye contenido y no está afiliada a
YouTube ni a Google.
