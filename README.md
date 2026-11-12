# 🎵 YouTube Music Downloader Web App

## 📄 Descripción
Aplicación web para descargar el audio de videos de YouTube de manera sencilla y con feedback en tiempo real. Permite obtener información del video, renombrar el archivo antes de la descarga y visualizar el progreso mediante una barra dinámica.

---

## ⚙️ Características
- Vista previa del video: título, duración, autor y miniatura.
- **Cola de descargas**: añade varias canciones sin esperar a que termine la anterior.
- **Historial visual persistente** con el estado real de cada descarga: En cola, Descargando %,
  Procesando (convirtiendo/metadatos), Descargado ✔ o Error. Se guarda en
  `%APPDATA%\DownloaderMusic\historial.json` y sobrevive a reinicios.
- **Una sola instancia**: si el puerto 5000 ya está en uso, la app avisa y no arranca otra copia.
- **Regla del nombre**: si el título no trae guion se autocompleta como `Autor - Título`; si ya
  trae guion se respeta. El icono **ⓘ** junto al nombre explica la regla.
- Carátula **1:1 de 1200×1200** incrustada en el `.m4a` (óptima para Apple Music/iPhone).
- Progreso, velocidad y ETA en tiempo real.
- Descarga automática de audio en `.m4a` dentro de `Descargas\DownloaderMusic`
  (la carpeta se crea sola si no existe).
- Botón 📁 en la barra superior para abrir la carpeta de descargas.
- Manejo de errores y alertas para enlaces inválidos o fallos de descarga.

---

## 🛠 Requisitos
- **Python:** 3.14.7 (probado)  
- **Librerías Python:**  
  - Flask  
  - yt-dlp  
  - mutagen  
  - requests  

Instalación de dependencias, clonación del repositorio y ejecución:

```bash
# Instalar dependencias
pip install Flask yt-dlp mutagen requests

# Clonar el repositorio
git clone https://github.com/EdgardSk8/Downloader-Music-Youtube.git
cd Downloader-Music-Youtube

# Ejecutar la aplicación (usar SIEMPRE el entorno virtual .venv)
.venv\Scripts\python.exe app.py
# Abrir http://127.0.0.1:5000 en el navegador
# Downloader-Music-Youtube
