def get_dark_theme() -> str:
    """
    Получает цветовые настройки для темной темы.
    Returns:
        str: строка настроек цветовой темы.
    """
    return """
        QMainWindow, QWidget { background-color: #2b2b2b; color: #d4d4d4; }
        QTreeWidget, QListWidget, QTextEdit, QLineEdit, QPlainTextEdit, QComboBox {
            background-color: #3c3c3c;
            color: #d4d4d4;
            border: 1px solid #555;
        }
        QTreeWidget::item:selected, QListWidget::item:selected {
            background-color: #4a6a9e;
        }
        QPushButton {
            background-color: #4a6a9e;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #5a7abe;
        }
        QLabel { color: #d4d4d4; }
        QMenuBar { background-color: #2b2b2b; color: #d4d4d4; }
        QMenuBar::item:selected { background-color: #4a6a9e; }
        QMenu { background-color: #2b2b2b; color: #d4d4d4; }
        QMenu::item:selected { background-color: #4a6a9e; }
    """


def get_light_theme() -> str:
    """
    Получает цветовые настройки для светлой темы.
    Returns:
        str: строка настроек цветовой темы.
    """
    return """
        QMainWindow, QWidget { background-color: #f0f0f0; color: #000; }
        QTreeWidget, QListWidget, QTextEdit, QLineEdit, QPlainTextEdit, QComboBox {
            background-color: white;
            color: black;
            border: 1px solid #ccc;
        }
        QTreeWidget::item:selected, QListWidget::item:selected {
            background-color: #aac8ff;
        }
        QPushButton {
            background-color: #e0e0e0;
            color: black;
            border: 1px solid #aaa;
            padding: 5px 10px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        QLabel { color: black; }
        QMenuBar { background-color: #f0f0f0; color: black; }
        QMenuBar::item:selected { background-color: #aac8ff; }
        QMenu { background-color: #f0f0f0; color: black; }
        QMenu::item:selected { background-color: #aac8ff; }
    """