; Instalador de YouTube Music Downloader (Inno Setup 6)
; Compilar con: .\build-installer.ps1   (pasa /DMyVersion=<versión> desde version.py)

#ifndef MyVersion
  #define MyVersion "0.0.0"
#endif

[Setup]
AppId={{6E5AA4C4-1AC2-4BF8-9079-744A398BE41A}
AppName=YouTube Music Downloader
AppVersion={#MyVersion}
AppVerName=YouTube Music Downloader {#MyVersion}
AppPublisher=EdgardSk8
AppPublisherURL=https://github.com/EdgardSk8/Downloader-Music-Youtube
AppSupportURL=https://github.com/EdgardSk8/Downloader-Music-Youtube
DefaultDirName={localappdata}\Programs\YouTube Music Downloader
DefaultGroupName=YouTube Music Downloader
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist
OutputBaseFilename=Instalador YouTube Music Downloader v{#MyVersion}
SetupIconFile=Downloader-ico.ico
UninstallDisplayIcon={app}\Downloader Music Youtube.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
MinVersion=10.0

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "dist\Portable\Downloader Music Youtube v{#MyVersion}.exe"; DestDir: "{app}"; DestName: "Downloader Music Youtube.exe"; Flags: ignoreversion
Source: "dist\Portable\ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Portable\ffprobe.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Portable\node\node.exe"; DestDir: "{app}\node"; Flags: ignoreversion
Source: "dist\Portable\LEEME.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\YouTube Music Downloader"; Filename: "{app}\Downloader Music Youtube.exe"; IconFilename: "{app}\Downloader Music Youtube.exe"
Name: "{autodesktop}\YouTube Music Downloader"; Filename: "{app}\Downloader Music Youtube.exe"; IconFilename: "{app}\Downloader Music Youtube.exe"

[Run]
Filename: "{app}\Downloader Music Youtube.exe"; Description: "Abrir YouTube Music Downloader"; Flags: nowait postinstall skipifsilent
