import logging
import sys

from PySide6.QtWidgets import QApplication

from database import init_db
from gui import MainWindow
from logger import setup_logging
from utils import get_db_path


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

    app = QApplication(sys.argv)
    window = MainWindow(engine)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
