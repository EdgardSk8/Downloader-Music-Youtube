#!/usr/bin/env bash
# Compila YouTube Music Downloader para Linux (binario + updater).
# Requisitos para usar la app: ffmpeg y nodejs.
#
#   sudo apt install ffmpeg nodejs
#   ./build-linux.sh
#
# El binario abre la interfaz en el navegador por defecto (no usa pywebview/GTK).

set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"

"$PYTHON" -m venv .venv-linux
# shellcheck disable=SC1091
source .venv-linux/bin/activate

python -m pip install -U pip
python -m pip install -U Flask yt-dlp mutagen pyinstaller

# 1) updater primero (el spec de la app lo incrusta como dist/updater)
pyinstaller updater.spec --noconfirm

# 2) app (en Linux usa launcher_linux.py: Flask + navegador)
pyinstaller "Downloader Music Youtube v1.1.5.spec" --noconfirm

VERSION="$(python -c 'import re; print(re.search(r"VERSION\s*=\s*\"([^\"]+)\"", open("version.py", encoding="utf-8").read()).group(1))')"

# 3) Icono + acceso de menú (opcional) junto al binario
cp static/iconos/icon-512.png "dist/downloader-music.png"
cat > "dist/Downloader Music Youtube.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=YouTube Music Downloader
Comment=Descarga audio de YouTube en M4A
Exec="$PWD/dist/Downloader Music Youtube v${VERSION}"
Icon=$PWD/dist/downloader-music.png
Terminal=true
Categories=AudioVideo;Audio;
EOF
chmod +x "dist/Downloader Music Youtube.desktop"

echo
echo "Listo: dist/Downloader Music Youtube v${VERSION}"
echo "Ejecuta: ./dist/\"Downloader Music Youtube v${VERSION}\""
echo "Recuerda: sudo apt install ffmpeg nodejs"
echo
echo "Para publicarlo como asset de Linux, renómbralo a:"
echo "  Downloader.Music.Youtube.v${VERSION}.linux-x86_64"
