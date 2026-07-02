import os
import sys
from pathlib import Path
from sqlalchemy.orm import Session
from PySide6.QtWidgets import QApplication

from database import init_db
from test_data import add_test_data
from gui import MainWindow


def get_db_path() -> Path:
    """
    Возвращает путь к файлу БД.
    Если приложение запущено как скомпилированный .exe, БД будет рядом с exe.
    Если как скрипт – в корне проекта (рядом с main.py).
    """
    if getattr(sys, 'frozen', False):
        # Запущено как .exe (PyInstaller)
        base_dir = Path(sys.executable).parent
    else:
        # Запущено как Python-скрипт
        base_dir = Path(__file__).parent
    return base_dir / 'projects.db'


def main():
    db_path = get_db_path()
    db_exists = db_path.exists()

    if not db_exists:
        print(f'База данных не найдена. Создаём новую в {db_path}')
        engine = init_db(str(db_path))
        # Заполняем тестовыми данными (для демонстрации)
        with Session(engine) as session:
            add_test_data(session)
        print('База данных создана и заполнена тестовыми данными.')
    else:
        print(f'База данных найдена. Подключаемся к {db_path}')
        engine = init_db(str(db_path))   # подключаемся, таблицы уже есть
        # Проверяем, пустая ли БД (нет проектов) – если да, можно добавить тестовые
        with Session(engine) as session:
            from database import Project
            if session.query(Project).count() == 0:
                print('БД пустая, добавляем тестовые данные.')
                add_test_data(session)

    # Здесь позже будет запуск GUI
    print('Приложение готово к работе.')
    # В будущем:
    # from ui import MainWindow
    app = QApplication(sys.argv)
    window = MainWindow(engine)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
