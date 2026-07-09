[Setup]
AppName=DevKeeperClient
AppVersion=1.0
DefaultDirName={autopf}\DevKeeperClient
DefaultGroupName=DevKeeperClient
UninstallDisplayIcon={app}\DevKeeperClient.exe
Compression=zip
SolidCompression=no
OutputDir=.
OutputBaseFilename=DevKeeperClient_Setup
SetupIconFile=main_icon.ico
WizardStyle=modern
PrivilegesRequired=admin
UninstallFilesDir={app}

[Files]
; Копируем всё из папки сборки (dist\DevKeeperClient) в каталог установки
Source: "dist\DevKeeperClient\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Ярлык в меню Пуск
Name: "{group}\DevKeeperClient"; Filename: "{app}\DevKeeperClient.exe"; IconFilename: "{app}\DevKeeperClient.exe"
; Ярлык на рабочем столе (будет создан только если пользователь поставит галочку)
Name: "{commondesktop}\DevKeeperClient"; Filename: "{app}\DevKeeperClient.exe"; IconFilename: "{app}\DevKeeperClient.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные задачи"

[Run]
; Запуск после установки, если пользователь поставил галочку
Filename: "{app}\DevKeeperClient.exe"; Description: "Запустить DevKeeperClient"; Flags: postinstall nowait skipifsilent

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
    Msg := 'Вы также хотите удалить все пользовательские данные (базу данных, шаблоны, логи) из папки:' + #13#10 +
           GetEnv('APPDATA') + '\DevKeeperClient' + #13#10#13#10 +
           'Если вы выберете "Да", все данные будут удалены без возможности восстановления.';
    Choice := MsgBox(Msg, mbConfirmation, MB_YESNO);
    DeleteUserData := (Choice = IDYES);
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    if DeleteUserData then
    begin
      AppDataPath := GetEnv('APPDATA') + '\DevKeeperClient';
      if DirExists(AppDataPath) then
      begin
        if DelTree(AppDataPath, True, True, True) then
          Log('Пользовательские данные удалены: ' + AppDataPath)
        else
          Log('Ошибка при удалении пользовательских данных: ' + AppDataPath);
      end;
    end;
  end;
end;