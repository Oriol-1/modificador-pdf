; Inno Setup Script para Modificador de PDF
; Genera instalador profesional para Windows 10/11
;
; Para compilar:
; 1. Descargar Inno Setup de https://jrsoftware.org/isinfo.php
; 2. Abrir este archivo con Inno Setup Compiler
; 3. Compilar (Ctrl+F9)

#define MyAppName "Modificador de PDF"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Modificador PDF"
#define MyAppURL "https://github.com/tu-usuario/modificador-pdf"
#define MyAppExeName "Modificador de PDF.exe"

[Setup]
; Identificador único de la aplicación
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Directorios
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Salida del instalador
OutputDir=..\dist\installer
OutputBaseFilename=ModificadorPDF_Setup_v{#MyAppVersion}

; Compresión
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Configuración visual
SetupIconFile=app_icon.ico
WizardStyle=modern
WizardSizePercent=100

; Privilegios
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Compatibilidad Windows
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Desinstalador
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Archivos del programa (desde la carpeta dist\ModificadorPDF)
Source: "..\dist\ModificadorPDF\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Icono en el menú inicio
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "Organizador de documentos PDF"

; Icono en el escritorio
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "Organizador de documentos PDF"

; Acceso rápido
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Ejecutar después de instalar
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Verificar si hay una versión anterior y desinstalarla
function InitializeSetup(): Boolean;
var
  UninstallKey: String;
  UninstallString: String;
  ResultCode: Integer;
begin
  Result := True;
  
  UninstallKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1';
  
  if RegQueryStringValue(HKLM, UninstallKey, 'UninstallString', UninstallString) or
     RegQueryStringValue(HKCU, UninstallKey, 'UninstallString', UninstallString) then
  begin
    if MsgBox('Se detectó una versión anterior de {#MyAppName}.' + #13#10 +
              '¿Desea desinstalarla antes de continuar?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      Exec(RemoveQuotes(UninstallString), '/SILENT', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
    end;
  end;
end;

[UninstallDelete]
; Limpiar configuración al desinstalar (opcional)
Type: filesandordirs; Name: "{localappdata}\ModificadorPDF"
