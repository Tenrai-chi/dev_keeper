[Setup]
AppName=DevKeeper
AppVersion=1.0
DefaultDirName={autopf}\DevKeeper
DefaultGroupName=DevKeeper
UninstallDisplayIcon={app}\DevKeeper.exe
Compression=zip
SolidCompression=no
OutputDir=.
OutputBaseFilename=DevKeeper_Setup
SetupIconFile=main_icon.ico
WizardStyle=modern
PrivilegesRequired=admin

[Files]
Source: "dist\DevKeeper\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\DevKeeper"; Filename: "{app}\DevKeeper.exe"; IconFilename: "{app}\DevKeeper.exe"
Name: "{commondesktop}\DevKeeper"; Filename: "{app}\DevKeeper.exe"; IconFilename: "{app}\DevKeeper.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные задачи"

[Run]
Filename: "{app}\DevKeeper.exe"; Description: "Запустить DevKeeper"; Flags: postinstall nowait skipifsilent

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
           GetEnv('APPDATA') + '\DevKeeper' + #13#10#13#10 +
           'Если вы выберете "Да", все данные будут удалены без возможности восстановления.';
    Choice := MsgBox(Msg, mbConfirmation, MB_YESNO);
    DeleteUserData := (Choice = IDYES);
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    if DeleteUserData then
    begin
      AppDataPath := GetEnv('APPDATA') + '\DevKeeper';
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