[Setup]
AppName=DevKeeper
AppVersion=1.0
DefaultDirName={autopf}\DevKeeper
DefaultGroupName=DevKeeper
UninstallDisplayIcon={app}\Client\DevKeeperClient.exe
Compression=zip
SolidCompression=no
OutputDir=.
OutputBaseFilename=DevKeeper_Setup
SetupIconFile=main_icon.ico
WizardStyle=modern
PrivilegesRequired=admin

[Types]
Name: "full"; Description: "Клиент и сервер"
Name: "client"; Description: "Только клиент"
Name: "server"; Description: "Только сервер"
Name: "custom"; Description: "Выборочная установка"; Flags: iscustom

[Components]
Name: "client"; Description: "DevKeeper Client (для подключения к серверу)"; Types: full client custom
Name: "server"; Description: "DevKeeper Server (запускается на основной машине)"; Types: full server custom

[Files]
; Клиент
Source: "dist\DevKeeperClient\*"; DestDir: "{app}\Client"; Components: client; Flags: ignoreversion recursesubdirs createallsubdirs
; Сервер
Source: "dist\DevKeeperServer\*"; DestDir: "{app}\Server"; Components: server; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Ярлыки для клиента
Name: "{group}\DevKeeperClient"; Filename: "{app}\Client\DevKeeperClient.exe"; Components: client
Name: "{commondesktop}\DevKeeperClient"; Filename: "{app}\Client\DevKeeperClient.exe"; Components: client; Tasks: desktopicon_client

; Ярлык для сервера
Name: "{group}\DevKeeperServer"; Filename: "{app}\Server\DevKeeperServer.exe"; Components: server

[Tasks]
Name: "desktopicon_client"; Description: "Создать ярлык DevKeeperClient на рабочем столе"; GroupDescription: "Дополнительные задачи"; Components: client

[Run]
; Запуск клиента после установки (если выбран)
Filename: "{app}\Client\DevKeeperClient.exe"; Description: "Запустить DevKeeperClient"; Components: client; Flags: postinstall nowait skipifsilent
; Запуск сервера (если выбран)
Filename: "{app}\Server\DevKeeperServer.exe"; Description: "Запустить DevKeeperServer"; Components: server; Flags: postinstall nowait skipifsilent

[Code]
var
  DeleteClientData: Boolean;
  DeleteServerData: Boolean;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ClientDataPath: string;
  ServerDataPath: string;
  Msg: string;
  Choice: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    Msg := 'Вы также хотите удалить все пользовательские данные (базу данных, шаблоны, логи) из папок:' + #13#10 + 
           GetEnv('APPDATA') + '\DevKeeperClient' + #13#10 +
           GetEnv('APPDATA') + '\DevKeeperServer' + #13#10#13#10 +
           'Если вы выберете "Да", все данные будут удалены без возможности восстановления.';
    Choice := MsgBox(Msg, mbConfirmation, MB_YESNO);
    DeleteClientData := (Choice = IDYES);
    DeleteServerData := (Choice = IDYES);
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    if DeleteClientData then
    begin
      ClientDataPath := GetEnv('APPDATA') + '\DevKeeperClient';
      if DirExists(ClientDataPath) then
      begin
        if DelTree(ClientDataPath, True, True, True) then
          Log('Данные клиента удалены: ' + ClientDataPath)
        else
          Log('Ошибка при удалении данных клиента: ' + ClientDataPath);
      end;
    end;
    if DeleteServerData then
    begin
      ServerDataPath := GetEnv('APPDATA') + '\DevKeeperServer';
      if DirExists(ServerDataPath) then
      begin
        if DelTree(ServerDataPath, True, True, True) then
          Log('Данные сервера удалены: ' + ServerDataPath)
        else
          Log('Ошибка при удалении данных сервера: ' + ServerDataPath);
      end;
    end;
  end;
end;