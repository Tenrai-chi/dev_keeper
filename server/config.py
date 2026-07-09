import os
import sys
import socket

from pathlib import Path


BASE_DIR = Path(__file__).parent
DATABASE_PATH = BASE_DIR / 'network_projects.db'
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'


def is_frozen() -> bool:
    """Возвращает True, если приложение запущено как .exe."""
    return getattr(sys, 'frozen', False)


def get_local_ip() -> str:
    """ Возвращает реальный IP-адрес в локальной сети. """

    try:
        # Подключаемся к внешнему серверу, чтобы получить реальный IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())


def get_app_data_dir() -> Path:
    """Возвращает папку для хранения данных сервера в AppData."""

    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', '')) / 'DevKeeperServer'
    else:
        base = Path.home() / '.local' / 'share' / 'DevKeeperServer'
    base.mkdir(parents=True, exist_ok=True)
    return base


class Settings:
    SERVER_HOST: str = os.getenv('SERVER_HOST', '0.0.0.0')
    SERVER_PORT: int = int(os.getenv('SERVER_PORT', 8888))

    if is_frozen():
        DATABASE_PATH: Path = get_app_data_dir() / 'network_projects.db'
    else:
        DATABASE_PATH: Path = Path(__file__).parent / 'network_projects.db'

    DATABASE_URL: str = f'sqlite:///{DATABASE_PATH}'

    CORS_ORIGINS: list = ['*']

    @property
    def local_ip(self) -> str:
        return get_local_ip()


settings = Settings()
