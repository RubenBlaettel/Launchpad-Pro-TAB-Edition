; ============================================================================
;  Launchpad Pro TAB Edition – Windows-Installer (Inno Setup 7)
; ============================================================================
;
;  Bauen (nach dem PyInstaller-Build):
;      python tools/build_installer.py
;  oder direkt:
;      ISCC /DAppVersion=1.1.0 packaging\windows\LaunchpadProTAB.iss
;
;  Ablauf für Anwender: Willkommen -> Zielordner (Standard: C:\Program Files) ->
;  Checkboxen Desktop-Verknüpfung / Startmenü / Dateizuordnung (alle an) -> Bereit ->
;  Installation. Ist das Programm bereits installiert, fragt der Installer zuerst:
;  „Aktualisieren“ oder „Deinstallieren“.
;
;  Deinstallation (Windows-Einstellungen › Apps oder erneuter Start des Installers):
;  Checkbox „Alle Projekte und Einstellungen löschen“ (Standard: aus).
;
;  Automatisches Update aus dem Programm heraus (still, mit Neustart):
;      LaunchpadProTAB-Setup-x.y.z.exe /SILENT /SUPPRESSMSGBOXES /NORESTART
;          /LPTABWAITPID=<Prozess-ID> /LPTABRESTART=1
;  Stille Deinstallation inkl. Benutzerdaten (für Tests/Administratoren):
;      unins000.exe /VERYSILENT /SUPPRESSMSGBOXES /LPTABPURGE=1
; ============================================================================

#if Ver < EncodeVer(7, 0, 0)
  #error "Inno Setup 7 oder neuer wird benötigt (https://jrsoftware.org/isdl.php)."
#endif
#ifndef AppVersion
  #error "AppVersion fehlt – z. B. ISCC /DAppVersion=1.1.0 LaunchpadProTAB.iss"
#endif
#ifndef AppVersionNumeric
  #define AppVersionNumeric AppVersion
#endif
#ifndef SourceDir
  #define SourceDir AddBackslash(SourcePath) + "..\..\dist\LaunchpadProTAB"
#endif
#ifndef OutputDir
  #define OutputDir AddBackslash(SourcePath) + "..\..\dist"
#endif

#define AppName "Launchpad Pro TAB Edition"
#define AppExe "LaunchpadProTAB.exe"
#define AppPublisher "TAB Theater"
#define AppURL "https://github.com/RubenBlaettel/Launchpad-Pro-TAB-Edition"
; Muss zu launchpad_pro_tab/system/integration.py passen:
#define AppUserModelId "TABTheater.LaunchpadProTAB"
#define AppMutexName "LaunchpadProTAB-Instanz"
#define ProgId "LaunchpadProTAB.Projekt"
; Niemals ändern – daran erkennt Windows die Installation (Updates, Deinstallation):
#define AppIdGuid "623A59DC-8E1B-496A-A80C-66ADADD7D898"

[Setup]
AppId={{{#AppIdGuid}}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
AppCopyright=© {#GetDateTimeString('yyyy', '', '')} {#AppPublisher}
AppComments=Touch-optimierte Launchpad-Software (Soundboard) für den Theaterbetrieb
VersionInfoVersion={#AppVersionNumeric}
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} – Installation
VersionInfoCompany={#AppPublisher}

; 64-Bit-Programm, Windows 10 (1809) oder neuer (Voraussetzung von Qt 6)
SetupArchitecture=x64
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763

; Für alle Benutzer nach C:\Program Files (Administratorrechte)
PrivilegesRequired=admin
DefaultDirName={autopf}\{#AppName}
DisableDirPage=auto
DisableProgramGroupPage=yes
DisableWelcomePage=no
UsePreviousTasks=yes

; Laufendes Programm erkennen (Mutex legt das Programm beim Start an)
AppMutex={#AppMutexName},Global\{#AppMutexName}
CloseApplications=yes
RestartApplications=no
ChangesAssociations=yes

UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}

; Aussehen: modern, folgt dem hellen/dunklen Windows-Design
WizardStyle=modern dynamic windows11
WizardImageFile=wizard-large.png
WizardSmallImageFile=wizard-small.png
SetupIconFile=..\..\launchpad_pro_tab\assets\app_icon.ico
ShowLanguageDialog=no

OutputDir={#OutputDir}
OutputBaseFilename=LaunchpadProTAB-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Messages]
german.WelcomeLabel2=Dieser Assistent installiert [name/ver] auf Ihrem Computer.%n%nLaunchpad Pro ist die Soundboard-Software für den Theaterbetrieb: Audiodateien auf Kacheln legen und per Tippen abspielen.
german.ConfirmUninstall=Soll %1 jetzt von diesem Computer entfernt werden?

[CustomMessages]
german.GroupShortcuts=Verknüpfungen:
german.GroupIntegration=Windows-Integration:
german.TaskDesktop=Desktop-Verknüpfung erstellen
german.TaskStartMenu=Im Startmenü anzeigen
german.TaskFileAssoc=Projektdateien (.lptab) per Doppelklick mit Launchpad Pro öffnen
german.ProjectFileType=Launchpad Pro TAB Projekt
german.ShortcutComment=Soundboard für den Theaterbetrieb
german.MaintenanceTitle=Launchpad Pro ist bereits installiert
german.MaintenanceSubtitle=Was möchten Sie tun?
german.MaintenanceText=Auf diesem Computer ist bereits Version %1 installiert.
german.MaintenanceUpdate=Aktualisieren bzw. reparieren (Version %1 installieren)
german.MaintenanceUninstall=Launchpad Pro deinstallieren
german.UninstallTitle=%1 deinstallieren
german.UninstallIntro=%1 wird von diesem Computer entfernt.%n%nIhre Projekte (Kacheln, Audiodateien, Coverbilder) und Einstellungen bleiben dabei normalerweise erhalten – zum Beispiel für eine spätere Neuinstallation.
german.UninstallPurge=Alle Projekte und Einstellungen ebenfalls löschen
german.UninstallPurgeDetail=Löscht alle Projektordner, die mit Launchpad Pro angelegt oder geöffnet wurden – samt der darin gespeicherten Audiodateien und Coverbilder – sowie alle Einstellungen. Exportierte ZIP-Dateien bleiben erhalten. Das Löschen kann nicht rückgängig gemacht werden.
german.ButtonContinue=&Weiter
german.ButtonCancel=Abbrechen

[Tasks]
Name: "desktopicon"; Description: "{cm:TaskDesktop}"; GroupDescription: "{cm:GroupShortcuts}"
Name: "startmenuicon"; Description: "{cm:TaskStartMenu}"; GroupDescription: "{cm:GroupShortcuts}"
Name: "fileassoc"; Description: "{cm:TaskFileAssoc}"; GroupDescription: "{cm:GroupIntegration}"

[InstallDelete]
; Programmdateien früherer Versionen vollständig ersetzen (keine veralteten Bibliotheken)
Type: filesandordirs; Name: "{app}\_internal"
; Abgewählte Verknüpfungen bei einer erneuten Installation entfernen
Type: files; Name: "{autodesktop}\{#AppName}.lnk"; Tasks: not desktopicon
Type: files; Name: "{autoprograms}\{#AppName}.lnk"; Tasks: not startmenuicon

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Comment: "{cm:ShortcutComment}"; AppUserModelID: "{#AppUserModelId}"; Tasks: startmenuicon
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Comment: "{cm:ShortcutComment}"; AppUserModelID: "{#AppUserModelId}"; Tasks: desktopicon

[Registry]
; „Ausführen“ (Win+R) kennt das Programm unter seinem Namen
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#AppExe}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#AppExe}"; ValueType: string; ValueName: "Path"; ValueData: "{app}"
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".lptab"; ValueData: ""
; Projektdateien (.lptab) öffnen
Root: HKA; Subkey: "Software\Classes\.lptab"; ValueType: string; ValueName: ""; ValueData: "{#ProgId}"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\.lptab\OpenWithProgids"; ValueType: string; ValueName: "{#ProgId}"; ValueData: ""; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueName: ""; ValueData: "{cm:ProjectFileType}"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\{#ProgId}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\{#ProgId}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: none; Flags: deletekey; Tasks: not fileassoc

[Run]
; Nach der normalen Installation: Checkbox „Launchpad Pro starten“
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
; Nach einem automatischen Update: als normaler Benutzer (nicht als Administrator) neu starten
Filename: "{app}\{#AppExe}"; Flags: nowait runasoriginaluser; Check: RestartAfterUpdate

[Code]
const
  SYNCHRONIZE = $00100000;
  WAIT_TIMEOUT = $00000102;
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{' + '{#AppIdGuid}' + '}_is1';

function OpenProcess(dwDesiredAccess: DWORD; bInheritHandle: Integer; dwProcessId: DWORD): THandle;
  external 'OpenProcess@kernel32.dll stdcall';
function WaitForSingleObject(hHandle: THandle; dwMilliseconds: DWORD): DWORD;
  external 'WaitForSingleObject@kernel32.dll stdcall';
function CloseHandle(hObject: THandle): Integer;
  external 'CloseHandle@kernel32.dll stdcall';

var
  MaintenancePage: TInputOptionWizardPage;
  CloseWithoutPrompt: Boolean;
  PurgeUserData: Boolean;

{ ---------------------------------------------------------------- Installation }

function RestartAfterUpdate(): Boolean;
begin
  Result := ExpandConstant('{param:LPTABRESTART|0}') = '1';
end;

{ Beim Update aus dem Programm heraus: warten, bis Launchpad Pro beendet ist.
  Muss vor der AppMutex-Prüfung passieren – die folgt direkt nach InitializeSetup. }
function InitializeSetup(): Boolean;
var
  Pid: Integer;
  Handle: THandle;
begin
  Result := True;
  Pid := StrToIntDef(ExpandConstant('{param:LPTABWAITPID|0}'), 0);
  if Pid > 0 then
  begin
    Log(Format('Warte auf das Beenden von Launchpad Pro (Prozess %d) ...', [Pid]));
    Handle := OpenProcess(SYNCHRONIZE, 0, Pid);
    if Handle <> 0 then
    begin
      if WaitForSingleObject(Handle, 60000) = WAIT_TIMEOUT then
        Log('Launchpad Pro wurde nach 60 s noch nicht beendet.');
      CloseHandle(Handle);
    end;
  end;
end;

function InstalledVersion(): String;
begin
  Result := '';
  RegQueryStringValue(HKA, UninstallKey, 'DisplayVersion', Result);
end;

function UninstallerPath(): String;
begin
  Result := '';
  if RegQueryStringValue(HKA, UninstallKey, 'UninstallString', Result) then
    Result := RemoveQuotes(Result);
end;

procedure InitializeWizard();
var
  Version: String;
begin
  Version := InstalledVersion();
  if (Version <> '') and FileExists(UninstallerPath()) then
  begin
    MaintenancePage := CreateInputOptionPage(wpWelcome,
      CustomMessage('MaintenanceTitle'), CustomMessage('MaintenanceSubtitle'),
      FmtMessage(CustomMessage('MaintenanceText'), [Version]), True, False);
    MaintenancePage.Add(FmtMessage(CustomMessage('MaintenanceUpdate'), ['{#AppVersion}']));
    MaintenancePage.Add(CustomMessage('MaintenanceUninstall'));
    MaintenancePage.SelectedValueIndex := 0;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  if (MaintenancePage <> nil) and (CurPageID = MaintenancePage.ID) and
     (MaintenancePage.SelectedValueIndex = 1) then
  begin
    { „Deinstallieren“ gewählt: vorhandenen Deinstaller starten und Setup schließen }
    Result := False;
    if Exec(UninstallerPath(), '', '', SW_SHOWNORMAL, ewNoWait, ResultCode) then
    begin
      CloseWithoutPrompt := True;
      WizardForm.Close;
    end else
      MsgBox(SysErrorMessage(ResultCode), mbError, MB_OK);
  end;
end;

procedure CancelButtonClick(CurPageID: Integer; var Cancel, Confirm: Boolean);
begin
  if CloseWithoutPrompt then
    Confirm := False;
end;

{ -------------------------------------------------------------- Deinstallation }

function AskUninstallOptions(): Boolean;
var
  Form: TSetupForm;
  Intro, Detail: TNewStaticText;
  PurgeBox: TNewCheckBox;
  ContinueButton, CancelButton: TNewButton;
  Margin, W: Integer;
begin
  Margin := ScaleX(20);
  Form := CreateCustomForm(ScaleX(500), ScaleY(246), False, False);
  try
    Form.Caption := FmtMessage(CustomMessage('UninstallTitle'), ['{#AppName}']);

    Intro := TNewStaticText.Create(Form);
    Intro.Parent := Form;
    Intro.AutoSize := False;
    Intro.WordWrap := True;
    Intro.Left := Margin;
    Intro.Top := ScaleY(18);
    Intro.Width := Form.ClientWidth - 2 * Margin;
    Intro.Caption := FmtMessage(CustomMessage('UninstallIntro'), ['{#AppName}']);
    Intro.AdjustHeight;

    PurgeBox := TNewCheckBox.Create(Form);
    PurgeBox.Parent := Form;
    PurgeBox.Left := Margin;
    PurgeBox.Top := Intro.Top + Intro.Height + ScaleY(16);
    PurgeBox.Width := Form.ClientWidth - 2 * Margin;
    PurgeBox.Height := ScaleY(22);
    PurgeBox.Caption := CustomMessage('UninstallPurge');
    PurgeBox.Checked := False;

    Detail := TNewStaticText.Create(Form);
    Detail.Parent := Form;
    Detail.AutoSize := False;
    Detail.WordWrap := True;
    Detail.Left := Margin + ScaleX(20);
    Detail.Top := PurgeBox.Top + PurgeBox.Height + ScaleY(4);
    Detail.Width := Form.ClientWidth - 2 * Margin - ScaleX(20);
    Detail.Caption := CustomMessage('UninstallPurgeDetail');
    Detail.Font.Size := Detail.Font.Size - 1;
    Detail.Enabled := False;
    Detail.AdjustHeight;

    ContinueButton := TNewButton.Create(Form);
    ContinueButton.Parent := Form;
    ContinueButton.Caption := CustomMessage('ButtonContinue');
    ContinueButton.ModalResult := mrOk;
    ContinueButton.Default := True;

    CancelButton := TNewButton.Create(Form);
    CancelButton.Parent := Form;
    CancelButton.Caption := CustomMessage('ButtonCancel');
    CancelButton.ModalResult := mrCancel;
    CancelButton.Cancel := True;

    W := Form.CalculateButtonWidth([ContinueButton.Caption, CancelButton.Caption]);
    CancelButton.Width := W;
    CancelButton.Height := ScaleY(26);
    CancelButton.Left := Form.ClientWidth - Margin - W;
    CancelButton.Top := Form.ClientHeight - ScaleY(26) - ScaleY(16);
    ContinueButton.Width := W;
    ContinueButton.Height := ScaleY(26);
    ContinueButton.Left := CancelButton.Left - ScaleX(8) - W;
    ContinueButton.Top := CancelButton.Top;

    Form.ActiveControl := ContinueButton;
    Form.FlipAndCenterIfNeeded(False, nil, False);
    Result := Form.ShowModal() = mrOk;
    if Result then
      PurgeUserData := PurgeBox.Checked;
  finally
    Form.Free();
  end;
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  PurgeUserData := ExpandConstant('{param:LPTABPURGE|0}') = '1';
  if not UninstallSilent() then
    Result := AskUninstallOptions();
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    { Zwischenspeicher immer entfernen: Update-Downloads und QML-Cache von Qt }
    DelTree(ExpandConstant('{localappdata}\LaunchpadProTAB'), True, True, True);
    DelTree(ExpandConstant('{localappdata}\{#AppPublisher}\{#AppName}'), True, True, True);
    RemoveDir(ExpandConstant('{localappdata}\{#AppPublisher}'));
  end;
  if not PurgeUserData then
    Exit;
  case CurUninstallStep of
    usUninstall:
      begin
        { Das Programm kennt alle Projektordner (Einstellungen) und löscht nur, was es
          selbst angelegt hat. Läuft, bevor die Programmdateien entfernt werden. }
        Log('Lösche Projekte und Einstellungen ...');
        if Exec(ExpandConstant('{app}\{#AppExe}'), '--purge-user-data --yes', '',
                SW_HIDE, ewWaitUntilTerminated, ResultCode) then
          Log(Format('Benutzerdaten gelöscht (Code %d).', [ResultCode]))
        else
          Log('Programm zum Löschen der Benutzerdaten nicht startbar: ' + SysErrorMessage(ResultCode));
      end;
    usPostUninstall:
      begin
        { Sicherheitsnetz: Einstellungen und Protokolle in jedem Fall entfernen }
        DelTree(ExpandConstant('{userappdata}\LaunchpadProTAB'), True, True, True);
      end;
  end;
end;
