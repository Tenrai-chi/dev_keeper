import sys
from PySide6.QtWidgets import QApplication
from client.gui import MainWindow
from client.logger import setup_logging


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    setup_logging()
    main()
