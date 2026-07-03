import logging
import sys

from datetime import datetime
from pathlib import Path


def get_logs_dir() -> Path:
    """ Возвращает путь к папке logs """

    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent
    logs_dir = base_dir / 'logs'
    logs_dir.mkdir(exist_ok=True)
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
    if not getattr(sys, 'frozen', False) or level <= logging.WARNING:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
