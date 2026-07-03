import logging
import sys

from pathlib import Path
from PySide6.QtWidgets import QApplication
from sqlalchemy.orm import Session

from database import init_db
from gui import MainWindow
from logger import setup_logging
from test_data import add_test_data


def get_db_path() -> Path:
    """
    Возвращает путь к файлу БД
    Если приложение запущено как исполняемый файл, БД будет рядом с exe
    Если как скрипт – в корне проекта рядом с main
    """

    if getattr(sys, 'frozen', False):
        # Исполняемый файл
        base_dir = Path(sys.executable).parent
    else:
        # Скрипт
        base_dir = Path(__file__).parent
    return base_dir / 'data' / 'projects.db'


def main():
    setup_logging()

    db_path = get_db_path()

    if not db_path.exists():
        logging.info(f'База данных не найдена. Создаём новую в {db_path}')
        engine = init_db(str(db_path))
        logging.info('База данных создана')

    else:
        logging.info(f'База данных найдена. Подключаемся к {db_path}')
        engine = init_db(str(db_path))
        logging.info('Подключение выполнено.')

    if '--test-data' in sys.argv:
        with Session(engine) as session:
            from database import Project
            if session.query(Project).count() == 0:
                add_test_data(session)
                logging.info('Добавлены тестовые данные')

    app = QApplication(sys.argv)
    window = MainWindow(engine)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
