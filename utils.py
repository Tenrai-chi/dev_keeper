import json
import logging
import os
import re
import sys
import shutil

from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)

STATUS_CHOICES: List[Tuple[str, str]] = [
    ('Новое', 'new'),
    ('В процессе', 'in_progress'),
    ('Готово', 'done'),
    ('Архивное', 'archived'),
]


def is_frozen() -> bool:
    """ Возвращает True, если приложение запущено как исполняемый файл .exe. """

    return getattr(sys, 'frozen', False)


def get_dev_dir() -> Path:
    """ Возвращает папку, в которой находится исполняемый файл (для exe) или проект (для скрипта) """

    if is_frozen():
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent


def get_internal_dir() -> Path:
    """ Возвращает папку _internal (для собранного приложения). """

    if is_frozen():
        return get_dev_dir() / '_internal'
    else:
        return get_dev_dir()


def get_app_data_dir() -> Path:
    """
    Возвращает папку для хранения пользовательских данных в AppData.
    Используется только в собранном приложении.
    """

    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', '')) / 'DevKeeper'
    else:
        base = Path.home() / '.local' / 'share' / 'DevKeeper'
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_db_path() -> Path:
    """
    Возвращает путь к файлу БД.
    - При разработке: data/projects.db (рядом с utils.py)
    - При установке: %APPDATA%/DevKeeper/projects.db
    Returns:
        Path: объект Path, указывающий на файл projects.db.
    """

    if is_frozen():
        return get_app_data_dir() / 'projects.db'
    else:
        return get_dev_dir() / 'data' / 'projects.db'


def get_default_tasks_path() -> Path:
    """
    Возвращает путь к файлу шаблонов задач default_tasks.json.
    - При разработке: data/files/default_tasks.json
    - При установке: %APPDATA%/DevKeeper/default_tasks.json
    Returns:
        Path: объект Path, указывающий на файл default_tasks.json.
    """

    if is_frozen():
        return get_app_data_dir() / 'default_tasks.json'
    else:
        return get_dev_dir() / 'data' / 'files' / 'default_tasks.json'


def get_icon_path() -> Path:
    """
    Возвращает путь к файлу иконки.
    - При разработке: data/images/main_icon.png
    - При установке: папка с exe
    """

    if is_frozen():
        return get_internal_dir() / 'main_icon.ico'
    else:
        return get_dev_dir() / 'data' / 'images' / 'main_icon.png'


def get_resources_dir() -> Path:
    """
    Возвращает папку с ресурсами (data) для копирования шаблонов при установке.
    - При разработке: data/
    - При установке: папка с exe (туда копируются все файлы из сборки)
    """

    if is_frozen():
        return get_internal_dir() / 'data'
    else:
        return get_dev_dir() / 'data'


def init_user_data():
    """
    Инициализирует пользовательские данные при первом запуске.
    - Создаёт папку AppData.
    - Копирует файл шаблонов из ресурсов (если есть) в AppData или создает новый.
    """

    if not is_frozen():
        return

    tasks_path = get_default_tasks_path()

    if not tasks_path.exists():
        src = get_resources_dir() / 'files' / 'default_tasks.json'
        if src.exists():
            shutil.copy(src, tasks_path)
            logger.info(f'Шаблон скопирован из {src} в {tasks_path}')
        else:
            with open(tasks_path, 'w', encoding='utf-8') as file:
                json.dump({'tasks': []}, file, ensure_ascii=False, indent=2)
            logger.info(f'Создан пустой файл шаблонов: {tasks_path}')


def parse_requirements(file_path: str) -> str | None:
    """
    Парсит requirements.txt и возвращает JSON-список библиотек.
    Если файл не найден, возвращает '[]'.
    Args:
        file_path: путь к файлу requirements.txt.

    Returns:
        str | None: JSON-список библиотек или None при ошибке
    """

    libraries = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Берём имя пакета до первого символа сравнения
                    pkg = re.split(r'[>=<~!]', line)[0].strip()
                    if pkg:
                        libraries.append(pkg)
    except FileNotFoundError:
        logger.error(f'Файл requirements не найден')
        return None
    except Exception as error:
        logger.error(f'Непредвиденная ошибка парсинга файла requirements: {error}')
        return None

    return json.dumps(libraries)


def status_to_display(status_code: str) -> str:
    """
     Преобразует код статуса в русское название.
    Args:
        status_code: код статуса (new, in_progress, done, archived).

    Returns:
         str: русское название статуса. Если код не найден, возвращает сам код.
    """

    for display, code in STATUS_CHOICES:
        if code == status_code:
            return display
    return status_code


def status_to_code(display_name: str) -> str:
    """
    Преобразует русское название статуса в его код.
    Args:
        display_name: русское название статуса (Новое, В процессе, Готово, Архивное).

    Returns:
        str: код статуса (new, in_progress, done, archived).
             Если название не найдено, возвращает 'new'.
    """

    for display, code in STATUS_CHOICES:
        if display == display_name:
            return code
    return 'new'


def load_templates() -> list[dict]:
    """
    Загружает список шаблонных задач из JSON-файла.

    Returns:
        list[dict]: список словарей с данными задач.
    """

    path = get_default_tasks_path()
    if not path.exists():
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('tasks', [])
    except Exception as error:
        logger.error(f'Ошибка загрузки шаблонов: {error}')
        return []


def save_templates(tasks: list[dict]) -> tuple[bool, str | None]:
    """
    Сохраняет список шаблонных задач в JSON-файл.
    Args:
        tasks: список словарей с данными задач.
    Returns:
        bool: True, если сохранет список шаблонов, иначе False
    """

    path = get_default_tasks_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, 'w', encoding='utf-8') as file:
            json.dump({'tasks': tasks}, file, ensure_ascii=False, indent=2)

        logger.info(f'Обновлен файл шаблонов задач.')
        return True, None
    except Exception as error:
        logger.error(f'Ошибка сохранения шаблонов: {error}')
        return False, str(error)
