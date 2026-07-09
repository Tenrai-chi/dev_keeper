[Setup]
AppName=DevKeeperServer
AppVersion=1.0
DefaultDirName={autopf}\DevKeeperServer
DefaultGroupName=DevKeeperServer
UninstallDisplayIcon={app}\DevKeeperServer.exe
Compression=zip
SolidCompression=no
OutputDir=.
OutputBaseFilename=DevKeeperServer_Setup
SetupIconFile=main_icon.ico
WizardStyle=modern
PrivilegesRequired=admin
UninstallFilesDir={app}

[Files]
; Копируем всё из папки сборки (dist\DevKeeperServer) в каталог установки
Source: "dist\DevKeeperServer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Ярлык в меню Пуск
Name: "{group}\DevKeeperServer"; Filename: "{app}\DevKeeperServer.exe"; IconFilename: "{app}\DevKeeperServer.exe"

[Run]
; Запуск после установки (опционально)
Filename: "{app}\DevKeeperServer.exe"; Description: "Запустить DevKeeperServer"; Flags: postinstall nowait skipifsilent

[Code]
var
  DeleteUserData: Boolean;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataPath: string;
  Msg: string;
  Choice: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    Msg := 'Вы также хотите удалить все данные сервера (базу данных, логи) из папки:' + #13#10 +
           GetEnv('APPDATA') + '\DevKeeperServer' + #13#10#13#10 +
           'Если вы выберете "Да", все данные будут удалены без возможности восстановления.';
    Choice := MsgBox(Msg, mbConfirmation, MB_YESNO);
    DeleteUserData := (Choice = IDYES);
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    if DeleteUserData then
    begin
      AppDataPath := GetEnv('APPDATA') + '\DevKeeperServer';
      if DirExists(AppDataPath) then
      begin
        if DelTree(AppDataPath, True, True, True) then
          Log('Данные сервера удалены: ' + AppDataPath)
        else
          Log('Ошибка при удалении данных сервера: ' + AppDataPath);
      end;
    end;
  end;
end;