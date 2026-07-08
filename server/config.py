import os
import sys

from pathlib import Path

BASE_DIR = Path(__file__).parent
DATABASE_PATH = BASE_DIR / 'network_projects.db'
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'


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
    SERVER_PORT: int = int(os.getenv('SERVER_PORT', 8000))

    DATABASE_PATH: Path = get_app_data_dir() / 'network_projects.db'
    DATABASE_URL: str = f'sqlite:///{DATABASE_PATH}'

    CORS_ORIGINS: list = ['*']


settings = Settings()
