# Compila el instalador de YouTube Music Downloader con Inno Setup.
# Usa la versión de version.py y exige que exista el paquete portable.

$ErrorActionPreference = "Stop"

$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path

$version = (Select-String -Path (Join-Path $raiz "version.py") `
    -Pattern 'VERSION\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value

$iscc = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    throw "Inno Setup no está instalado (ISCC.exe no encontrado). Instálalo con: winget install JRSoftware.InnoSetup"
}

$exePortable = Join-Path $raiz "dist\Portable\Downloader Music Youtube v$version.exe"
if (-not (Test-Path $exePortable)) {
    throw "Falta dist\Portable\Downloader Music Youtube v$version.exe. Compila la app y arma el paquete portable."
}

& $iscc "/DMyVersion=$version" (Join-Path $raiz "installer.iss")
if ($LASTEXITCODE -ne 0) {
    throw "ISCC falló con código $LASTEXITCODE."
}

$salida = Join-Path $raiz "dist\Instalador YouTube Music Downloader v$version.exe"
if (-not (Test-Path $salida)) {
    throw "No se generó el instalador."
}

"Instalador creado: $salida"
