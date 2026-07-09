import logging
import sys
from PySide6.QtWidgets import QApplication
from client.gui import MainWindow

logger = logging.getLogger('Client_MAIN')


def main():
    logger.info(f'Запуск приложения...')
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
