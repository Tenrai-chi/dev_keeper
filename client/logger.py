import logging
import sys
import os

from datetime import datetime
from pathlib import Path


def get_app_data_dir() -> Path:
    """ Возвращает папку для хранения данных приложения в AppData. """

    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', '')) / 'DevKeeper'
    else:
        base = Path.home() / '.local' / 'share' / 'DevKeeper'
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_logs_dir() -> Path:
    """
    Возвращает путь к папке client_logs.
    - При разработке: client_logs/ (рядом с файлом)
    - В собранном приложении: %APPDATA%/DevKeeper/logs
    Returns:
        Path: путь к папке с логами
    """

    if getattr(sys, 'frozen', False):
        logs_dir = get_app_data_dir() / 'client_logs'
    else:
        logs_dir = Path(__file__).parent / 'client_logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def setup_logging(level: str = None) -> None:
    """
    Настраивает логирование: вывод в консоль и в файл с ротацией по дням.
    Если уровень не указан, то:
        - для .exe: WARNING
        - для скрипта: INFO
    Args:
        level: заданный уровень логирования
    """

    if level is None:
        if getattr(sys, 'frozen', False):
            level = logging.WARNING
        else:
            level = logging.INFO

    logs_dir = get_logs_dir()
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = logs_dir / f'{today}.log'

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Настройка для записи в файл
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Настройка для записи в консоль
    if not getattr(sys, 'frozen', False) or level <= logging.DEBUG:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
