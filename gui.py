import json
import logging
import sys

from sqlalchemy.orm import Session
from pathlib import Path
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QListWidget,
    QTextEdit, QPushButton, QSplitter, QLabel, QMessageBox,
    QFileDialog, QDialog, QLineEdit, QPlainTextEdit,
    QDialogButtonBox, QFormLayout, QCheckBox, QComboBox,
    QStackedWidget, QApplication, QFrame,
    QListWidgetItem
)

from database import parse_requirements
from crud import (
    get_all_projects, get_project_by_id, add_project, delete_project,
    update_project, toggle_favorite, get_tasks_by_project,
    get_task_by_id, add_task, update_task, delete_task,
    archive_task, unarchive_task, change_task_status,
    reorder_tasks, search_projects
)

logger = logging.getLogger(__name__)
status_translation = {
    'new': 'Новое',
    'in_progress': 'В процессе',
    'done': 'Готово',
    'archived': 'Архивное'
}


class MainWindow(QMainWindow):
    STATUS_CHOICES = [
        ('Новое', 'new'),
        ('В процессе', 'in_progress'),
        ('Готово', 'done'),
        ('Архивное', 'archived'),
    ]

    @staticmethod
    def status_to_display(status_code: str) -> str:
        """ Возвращает русское название статуса по коду """

        for display, code in MainWindow.STATUS_CHOICES:
            if code == status_code:
                return display
        return status_code

    @staticmethod
    def status_to_code(display_name: str) -> str:
        """ Возвращает код статуса по русскому названию """

        for display, code in MainWindow.STATUS_CHOICES:
            if display == display_name:
                return code
        return 'new'

    def __init__(self, engine):
        """ Инициализация главного окна, загрузка сохраненной темы и запуск интерфейса """

        super().__init__()
        self.engine = engine
        self.current_project_id = None
        self.current_task_id = None
        self.settings = QSettings('DevKeeper', 'Settings')
        self.current_theme = self.settings.value('theme', 'system')
        self.current_search_text = ''
        self.right_splitter = None
        self.task_fields_splitter = None

        self.setWindowTitle('DevKeeper')
        self.setMinimumSize(1000, 700)
        geometry = self.settings.value('main_window_geometry')
        if geometry is not None:
            self.restoreGeometry(geometry)

        self._setup_menu()
        self._setup_ui()
        self._apply_theme(self.current_theme)
        self._load_projects()

    @staticmethod
    def _create_button_box() -> QDialogButtonBox:
        """ Создаёт кнопки ОК и Отмена с русскими подписями """

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText('ОК')
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText('Отмена')
        return button_box

    def _question_dialog(self, title: str, text: str) -> int:
        """
        Показывает диалог с вопросом и кнопками Да / Нет.
        Возвращает QMessageBox.YesRole или QMessageBox.NoRole.
        """

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.button(QMessageBox.StandardButton.Yes).setText('Да')
        msg_box.button(QMessageBox.StandardButton.No).setText('Нет')
        msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
        return msg_box.exec()

    def _setup_menu(self):
        """ Создает меню настроек с выбором темы """

        menubar = self.menuBar()
        settings_menu = menubar.addMenu('⚙️ Настройки')

        theme_submenu = settings_menu.addMenu('Тема')
        for theme_name, label in [('light', 'Светлая'), ('dark', 'Тёмная'), ('system', 'Системная')]:
            action = QAction(label, self)
            action.triggered.connect(lambda checked, t=theme_name: self._apply_theme(t))
            theme_submenu.addAction(action)

        templates_action = QAction('📋 Управление шаблонами задач...', self)
        templates_action.triggered.connect(self._open_template_manager)
        settings_menu.addSeparator()
        settings_menu.addAction(templates_action)

    def _open_template_manager(self):
        dialog = TemplateManagerDialog(self)
        dialog.exec()

    def _apply_theme(self, theme_name):
        """ Применяет и сохраняет выбранную тему в настройках приложения """

        self.current_theme = theme_name
        if theme_name == 'system':
            if QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
                theme_name = 'dark'
            else:
                theme_name = 'light'
        if theme_name == 'dark':
            self.setStyleSheet("""
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
            """)
        else:
            self.setStyleSheet("""
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
            """)
        self.settings.setValue("theme", self.current_theme)

    def _setup_ui(self):
        """ Создает и размещает все виджеты главного окна """

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        central_widget.setLayout(QVBoxLayout())
        central_widget.layout().addWidget(main_splitter)

        left_widget = self._create_left_panel()
        main_splitter.addWidget(left_widget)

        right_widget = self._create_right_panel()
        main_splitter.addWidget(right_widget)

        main_splitter.setSizes([300, 700])

    def _create_left_panel(self):
        """ Создает левую панель с деревом проектов и кнопками управления """

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        label = QLabel('📁 Проекты')
        label.setStyleSheet('font-weight: bold; font-size: 14px;')
        layout.addWidget(label)

        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText('🔍 Поиск по названию или технологиям...')
        self.search_line.textChanged.connect(self._on_search_text_changed)
        layout.addWidget(self.search_line)

        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderHidden(True)
        self.project_tree.setIndentation(15)
        self.project_tree.itemClicked.connect(self._on_project_selected)
        self.project_tree.itemDoubleClicked.connect(self._toggle_favorite)

        layout.addWidget(self.project_tree, stretch=1)

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(5)

        btn_add = QPushButton('➕ Добавить')
        btn_add.clicked.connect(self._add_project_dialog)
        btn_layout.addWidget(btn_add)

        btn_del = QPushButton('🗑️ Удалить')
        btn_del.clicked.connect(self._delete_project)
        btn_layout.addWidget(btn_del)

        btn_open = QPushButton('🚀 Открыть в PyCharm')
        btn_open.clicked.connect(self._open_in_pycharm)
        btn_layout.addWidget(btn_open)

        btn_edit = QPushButton('✏️ Редактировать')
        btn_edit.clicked.connect(self._edit_project_dialog)
        btn_layout.addWidget(btn_edit)

        layout.addLayout(btn_layout)
        return widget

    def _create_right_panel(self):
        """
        Создает правую панель, которая содержит:
            - список задач
            - кнопки управления
            - описание проекта / задач
        """

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        header_layout = QHBoxLayout()
        label = QLabel('📋 Задачи')
        label.setStyleSheet('font-weight: bold; font-size: 14px;')
        header_layout.addWidget(label)
        header_layout.addStretch()
        self.show_archived_check = QCheckBox('Показать архивные')
        self.show_archived_check.stateChanged.connect(self._reload_tasks)
        header_layout.addWidget(self.show_archived_check)

        btn_template = QPushButton('📋 Шаблоны')
        btn_template.clicked.connect(self._add_tasks_from_template)
        header_layout.addWidget(btn_template)

        layout.addLayout(header_layout)

        self.task_list = QListWidget()
        self.task_list.itemClicked.connect(self._on_task_selected)
        self.task_list.itemDoubleClicked.connect(self._toggle_task_favorite)
        layout.addWidget(self.task_list)

        task_btn_layout = QHBoxLayout()
        btn_add_task = QPushButton('➕ Добавить')
        btn_add_task.clicked.connect(self._add_task_dialog)
        task_btn_layout.addWidget(btn_add_task)

        btn_archive = QPushButton('📦 В архив')
        btn_archive.clicked.connect(self._archive_task)
        task_btn_layout.addWidget(btn_archive)

        btn_unarchive = QPushButton('↩️ Восстановить')
        btn_unarchive.clicked.connect(self._unarchive_task)
        task_btn_layout.addWidget(btn_unarchive)

        btn_delete_task = QPushButton('❌ Удалить')
        btn_delete_task.clicked.connect(self._delete_task)
        task_btn_layout.addWidget(btn_delete_task)

        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addLayout(header_layout)
        top_layout.addWidget(self.task_list)
        top_layout.addLayout(task_btn_layout)

        self.details_stack = QStackedWidget()
        self.details_stack.addWidget(self._create_task_details_panel())
        self.details_stack.addWidget(self._create_project_details_panel())

        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addWidget(self.details_stack)

        # ----- Сплиттер между верхом и низом -----
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.addWidget(top_widget)
        self.right_splitter.addWidget(bottom_widget)
        self.right_splitter.setStretchFactor(0, 1)
        self.right_splitter.setStretchFactor(1, 2)
        self.right_splitter.setChildrenCollapsible(False)

        layout.addWidget(self.right_splitter)

        state = self.settings.value('right_splitter_state')
        if state is not None:
            self.right_splitter.restoreState(state)
        else:
            self.right_splitter.setSizes([300, 600])

        self.right_splitter.splitterMoved.connect(self._save_right_splitter_state)

        self._clear_details()
        return widget

    def _create_task_details_panel(self):
        """ Создает панель для редактирования и просмотра деталей задачи """

        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel('Заголовок:'))
        self.detail_title = QLineEdit()
        layout.addWidget(self.detail_title)

        # ---- Сплиттер для трёх полей ----
        fields_splitter = QSplitter(Qt.Orientation.Vertical)

        # Описание
        desc_widget = QWidget()
        desc_layout = QVBoxLayout(desc_widget)
        desc_layout.addWidget(QLabel('Описание:'))
        self.detail_description = QTextEdit()
        self.detail_description.setMinimumHeight(60)
        desc_layout.addWidget(self.detail_description)
        fields_splitter.addWidget(desc_widget)

        # Заметка
        note_widget = QWidget()
        note_layout = QVBoxLayout(note_widget)
        note_layout.addWidget(QLabel('Заметка:'))
        self.detail_note = QTextEdit()
        self.detail_note.setMinimumHeight(60)
        note_layout.addWidget(self.detail_note)
        fields_splitter.addWidget(note_widget)

        # Код
        code_widget = QWidget()
        code_layout = QVBoxLayout(code_widget)
        code_layout.addWidget(QLabel('Код:'))
        self.detail_code = QTextEdit()
        self.detail_code.setFontFamily('Courier New')
        self.detail_code.setMinimumHeight(80)
        code_layout.addWidget(self.detail_code)
        fields_splitter.addWidget(code_widget)

        fields_splitter.setStretchFactor(0, 1)
        fields_splitter.setStretchFactor(1, 1)
        fields_splitter.setStretchFactor(2, 2)
        fields_splitter.setChildrenCollapsible(False)

        layout.addWidget(fields_splitter)

        # Статус и кнопка
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel('Статус:'))
        self.status_combo = QComboBox()
        for display_name, _ in self.STATUS_CHOICES:
            self.status_combo.addItem(display_name)
        status_layout.addWidget(self.status_combo)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        btn_save = QPushButton('💾 Сохранить изменения')
        btn_save.clicked.connect(self._save_task_details)
        layout.addWidget(btn_save)

        # Восстанавливаем состояние
        state = self.settings.value('task_fields_splitter_state')
        if state is not None:
            fields_splitter.restoreState(state)
        else:
            fields_splitter.setSizes([150, 150, 300])

        fields_splitter.splitterMoved.connect(self._save_task_fields_splitter_state)

        # Сохраняем ссылку для доступа в методах сохранения
        self.task_fields_splitter = fields_splitter

        return widget

    def _create_project_details_panel(self):
        """ Создает панель для редактирования и просмотра деталей проекта """

        widget = QWidget()
        layout = QFormLayout(widget)

        self.proj_display_name = QLineEdit()
        self.proj_display_name.setReadOnly(True)
        layout.addRow('Название:', self.proj_display_name)

        self.proj_tech_name = QLineEdit()
        self.proj_tech_name.setReadOnly(True)
        layout.addRow('Техническое имя:', self.proj_tech_name)

        self.proj_path = QLineEdit()
        self.proj_path.setReadOnly(True)
        layout.addRow('Путь:', self.proj_path)

        self.proj_description = QTextEdit()
        self.proj_description.setReadOnly(True)
        layout.addRow('Описание:', self.proj_description)

        self.proj_technologies = QTextEdit()
        self.proj_technologies.setReadOnly(True)
        self.proj_technologies.setMaximumHeight(100)
        layout.addRow('Технологии:', self.proj_technologies)

        self.btn_refresh_tech = QPushButton('🔄 Обновить технологии (из requirements.txt)')
        self.btn_refresh_tech.clicked.connect(self._refresh_technologies)
        layout.addRow('', self.btn_refresh_tech)

        return widget

    def _load_projects(self):
        """ Загружает все проекты и выводит в дереве проектов """

        self.project_tree.clear()
        with Session(self.engine) as session:
            if self.current_search_text:
                projects = search_projects(session, self.current_search_text)
            else:
                projects = get_all_projects(session)
            for project in projects:
                text = f'⭐ {project.display_name}' if project.is_favorite else project.display_name
                item = QTreeWidgetItem([text])
                item.setData(0, Qt.ItemDataRole.UserRole, project.id)
                self.project_tree.addTopLevelItem(item)

        if self.project_tree.topLevelItemCount() > 0:
            self.project_tree.setCurrentItem(self.project_tree.topLevelItem(0))
            self._on_project_selected(self.project_tree.topLevelItem(0))

    def _load_tasks(self, project_id: int):
        """ Загружает все задачи выбранного проекта и выводит в дереве проектов """

        self.task_list.clear()
        self.current_project_id = project_id
        include_archived = self.show_archived_check.isChecked()
        with Session(self.engine) as session:
            tasks = get_tasks_by_project(session, project_id, include_archived=include_archived)
            for task in tasks:
                star = '⭐ ' if task.is_favorite else ''
                display_text = f'{star}{task.title} [{self.status_to_display(task.status)}]'
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, task.id)

                if task.status == 'archived':
                    item.setForeground(Qt.GlobalColor.gray)
                elif task.status == 'done':
                    item.setForeground(Qt.GlobalColor.darkGreen)
                elif task.status == 'in_progress':
                    item.setForeground(Qt.GlobalColor.darkBlue)
                elif task.status == 'review':
                    item.setForeground(Qt.GlobalColor.darkYellow)

                self.task_list.addItem(item)

        self._clear_details()
        self.current_task_id = None

    def _reload_tasks(self):
        """ Перезагружает список задач при изменении флага "Показать архивные" """

        if self.current_project_id is not None:
            self._load_tasks(self.current_project_id)

    def _on_project_selected(self, item: QTreeWidgetItem, column: int = 0):
        """ Загружает и выводит информацию о проекте при клике по нему в дереве проектов """

        project_id = item.data(column, Qt.ItemDataRole.UserRole)
        if project_id is not None:
            self._load_tasks(project_id)
            self._show_project_info(project_id)

    def _on_task_selected(self, item: QListWidgetItem):
        """ Загружает и выводит информацию о задаче при клике на задачу в списке """

        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id is not None:
            self.current_task_id = task_id
            self._show_task_info(task_id)

    def _show_project_info(self, project_id: int):
        """ Отображает информацию о проекте в панели деталей """

        self.details_stack.setCurrentIndex(1)
        with Session(self.engine) as session:
            project = get_project_by_id(session, project_id)
            if project:
                self.proj_display_name.setText(project.display_name)
                self.proj_tech_name.setText(project.tech_name)
                self.proj_path.setText(project.path)
                self.proj_description.setPlainText(project.description)
                try:
                    techs = json.loads(project.technologies)
                    self.proj_technologies.setPlainText(', '.join(techs))
                except json.JSONDecodeError:
                    self.proj_technologies.setPlainText('(ошибка загрузки)')
                    logger.warning(f'Не удалось разобрать технологии проекта {project.id}: {project.technologies}')
                    QMessageBox.warning(
                        self,
                        'Ошибка данных',
                        f'Не удалось прочитать список технологий для проекта "{project.display_name}".\n'
                        'Данные повреждены. Вы можете исправить их вручную в режиме редактирования.'
                    )
                except Exception as error:
                    logger.warning(f'Не удалось разобрать технологии проекта {project.id}: {project.technologies}.'
                                   f'По причине: {error}')

    def _show_task_info(self, task_id: int):
        """ Отображает информацию о задаче в панели редактирования задачи """

        self.details_stack.setCurrentIndex(0)
        with Session(self.engine) as session:
            task = get_task_by_id(session, task_id)
            if task:
                self.detail_title.setText(task.title)
                self.detail_description.setPlainText(task.description)
                self.detail_note.setPlainText(task.note)
                self.detail_code.setPlainText(task.code_snippet)
                display_name = self.status_to_display(task.status)
                idx = self.status_combo.findText(display_name)
                if idx >= 0:
                    self.status_combo.setCurrentIndex(idx)
                self.detail_title.setReadOnly(False)
                self.detail_description.setReadOnly(False)
                self.detail_note.setReadOnly(False)
                self.detail_code.setReadOnly(False)
                self.status_combo.setEnabled(True)

    def _clear_details(self):
        """ Очищает панель деталей и переводит в режим "только для чтения" для просмотра информации о проекте """

        self.details_stack.setCurrentIndex(0)
        self.detail_title.clear()
        self.detail_description.clear()
        self.detail_note.clear()
        self.detail_code.clear()
        self.detail_title.setReadOnly(True)
        self.detail_description.setReadOnly(True)
        self.detail_note.setReadOnly(True)
        self.detail_code.setReadOnly(True)
        self.status_combo.setEnabled(False)
        self.proj_display_name.clear()
        self.proj_tech_name.clear()
        self.proj_path.clear()
        self.proj_description.clear()
        self.proj_technologies.clear()

    def _save_task_details(self):
        """ сохраняет изменения в текущей задаче из панели редактирования """

        if self.current_task_id is None:
            QMessageBox.warning(self, 'Нет задачи', 'Выберите задачу для редактирования.')
            return
        with Session(self.engine) as session:
            task = get_task_by_id(session, self.current_task_id)
            if task:
                task.title = self.detail_title.text()
                task.description = self.detail_description.toPlainText()
                task.note = self.detail_note.toPlainText()
                task.code_snippet = self.detail_code.toPlainText()
                new_status_display = self.status_combo.currentText()
                new_status = self.status_to_code(new_status_display)
                if task.status != new_status:
                    change_task_status(session, self.current_task_id, new_status)
                else:
                    session.commit()
                self._load_tasks(self.current_project_id)
                QMessageBox.information(self, 'Сохранено', 'Изменения сохранены.')

    def _add_project_dialog(self) -> None:
        """ Открывает диалог для добавления нового проекта """

        dialog = QDialog(self)
        dialog.setWindowTitle('Добавить проект')
        layout = QFormLayout(dialog)

        display_name_edit = QLineEdit()
        layout.addRow('Отображаемое имя:', display_name_edit)

        path_label = QLabel('Папка не выбрана')
        btn_choose = QPushButton('Выбрать папку...')
        chosen_path = []

        def choose_folder():
            folder = QFileDialog.getExistingDirectory(dialog, 'Выбрать папку проекта')
            if folder:
                chosen_path.append(folder)
                path_label.setText(folder)
                tech_name_from_folder = Path(folder).name
                if not display_name_edit.text():
                    display_name_edit.setText(tech_name_from_folder)

        btn_choose.clicked.connect(choose_folder)
        layout.addRow('Путь к проекту:', btn_choose)
        layout.addRow('', path_label)

        tech_name_edit = QLineEdit()
        tech_name_edit.setPlaceholderText('будет взято из имени папки')
        layout.addRow('Техническое имя (опционально):', tech_name_edit)

        description_edit = QPlainTextEdit()
        description_edit.setPlaceholderText('Краткое описание проекта...')
        layout.addRow('Описание:', description_edit)

        button_box = self._create_button_box()
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            if not chosen_path[0]:
                QMessageBox.warning(self, 'Ошибка', 'Выберите папку проекта.')
                return
            display_name = display_name_edit.text().strip()
            if not display_name:
                QMessageBox.warning(self, 'Ошибка', 'Введите отображаемое имя.')
                return

            tech_name = tech_name_edit.text().strip()
            if not tech_name:
                tech_name = Path(chosen_path[0]).name

            description = description_edit.toPlainText().strip()

            req_path = Path(chosen_path[0]) / 'requirements.txt'
            tech_json = parse_requirements(str(req_path))
            if tech_json is None:
                tech_json = '[]'
                QMessageBox.warning(
                    self,
                    'Предупреждение',
                    'Не удалось прочитать файл requirements.txt.\n'
                    'Технологии не будут добавлены. Вы сможете добавить их позже вручную.'
                )

            with Session(self.engine) as session:
                add_project(
                    session,
                    tech_name=tech_name,
                    display_name=display_name,
                    path=chosen_path[0],
                    description=description,
                    technologies=tech_json
                )

            self._load_projects()
            QMessageBox.information(self, 'Готово', f'Проект "{display_name}" добавлен.')

    @staticmethod
    def _get_default_tasks_path() -> Path:
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent
        return base_dir / 'data' / 'files' / 'default_tasks.json'

    def _load_templates(self) -> list[dict]:
        path = self._get_default_tasks_path()
        if not path.exists():
            return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('tasks', [])
        except Exception as e:
            logger.error(f"Ошибка загрузки шаблонов: {e}")
            return []

    def _save_templates(self, tasks: list[dict]) -> None:
        path = self._get_default_tasks_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, 'w', encoding='utf-8') as file:
                json.dump({'tasks': tasks}, file, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения шаблонов: {e}")
            QMessageBox.critical(self, 'Ошибка', f'Не удалось сохранить шаблоны:\n{e}')

    def _delete_project(self) -> None:
        """ Удаляет выбранный проект после подтверждения """

        current_item = self.project_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Нет проекта', 'Выберите проект для удаления.')
            return
        project_id = current_item.data(0, Qt.ItemDataRole.UserRole)
        if not project_id:
            return

        reply = self._question_dialog(
            'Удаление проекта',
            'Вы уверены, что хотите удалить проект и все его задачи?'
        )

        if reply == QMessageBox.StandardButton.Yes:
            with Session(self.engine) as session:
                delete_project(session, project_id)
            self._load_projects()
            QMessageBox.information(self, 'Удалено', 'Проект удалён.')

    def _add_task_dialog(self):
        """ Открывает диалог добавления новой задачи в текущий проект """

        if self.current_project_id is None:
            QMessageBox.warning(self, 'Нет проекта', 'Сначала выберите проект в дереве.')
            return

        dialog = QDialog(self)
        dialog.setWindowTitle('Добавить задачу')
        layout = QFormLayout(dialog)

        title_edit = QLineEdit()
        layout.addRow('Заголовок:', title_edit)

        description_edit = QPlainTextEdit()
        description_edit.setPlaceholderText('Описание задачи...')
        layout.addRow('Описание:', description_edit)

        note_edit = QPlainTextEdit()
        note_edit.setPlaceholderText('Заметки, идеи, ссылки...')
        layout.addRow('Заметка:', note_edit)

        code_edit = QPlainTextEdit()
        code_edit.setPlaceholderText('Код (если есть)...')
        layout.addRow('Код:', code_edit)

        button_box = self._create_button_box()
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            title = title_edit.text().strip()
            if not title:
                QMessageBox.warning(self, 'Ошибка', 'Введите заголовок задачи.')
                return

            with Session(self.engine) as session:
                add_task(
                    session,
                    project_id=self.current_project_id,
                    title=title,
                    description=description_edit.toPlainText().strip(),
                    note=note_edit.toPlainText().strip(),
                    code_snippet=code_edit.toPlainText().strip(),
                    status='new'
                )
            self._load_tasks(self.current_project_id)

    def _archive_task(self) -> None:
        """ Перемещает выбранную задачу в архив """

        current_item = self.task_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Нет задачи', 'Выберите задачу для архивации.')
            return
        task_id = current_item.data(Qt.ItemDataRole.UserRole)
        with Session(self.engine) as session:
            archive_task(session, task_id)
        self._load_tasks(self.current_project_id)

    def _unarchive_task(self):
        """ Восстанавливает выбранную архивную задачу, устанавливая статус выполнения done """

        current_item = self.task_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Нет задачи', 'Выберите задачу для восстановления.')
            return
        task_id = current_item.data(Qt.ItemDataRole.UserRole)
        with Session(self.engine) as session:
            unarchive_task(session, task_id)
        self._load_tasks(self.current_project_id)

    def _delete_task(self):
        """ Удаляет выбранную задачу после подтверждения """

        current_item = self.task_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Нет задачи', 'Выберите задачу для удаления.')
            return
        task_id = current_item.data(Qt.ItemDataRole.UserRole)
        reply = self._question_dialog(
            'Удаление задачи',
            'Вы уверены, что хотите безвозвратно удалить эту задачу?'
        )

        if reply == QMessageBox.StandardButton.Yes:
            with Session(self.engine) as session:
                delete_task(session, task_id)
            self._load_tasks(self.current_project_id)
            QMessageBox.information(self, 'Удалено', 'Задача удалена.')
        self._load_tasks(self.current_project_id)

    def _toggle_favorite(self, item: QTreeWidgetItem, column: int = None) -> None:
        """ Переключает статус избранного у выбранного проекта по двойному клику """

        project_id = item.data(column, Qt.ItemDataRole.UserRole)
        if project_id is None:
            return
        with Session(self.engine) as session:
            toggle_favorite(session, project_id)
        current_id = project_id
        self._load_projects()

        for i in range(self.project_tree.topLevelItemCount()):
            it = self.project_tree.topLevelItem(i)
            if it.data(0, Qt.ItemDataRole.UserRole) == current_id:
                self.project_tree.setCurrentItem(it)
                self._on_project_selected(it)
                break

    def _toggle_task_favorite(self, item: QListWidgetItem):
        """ Переключает статус избранного у выбранной задачи по двойному клику """

        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id is None:
            return
        with Session(self.engine) as session:
            task = get_task_by_id(session, task_id)
            if task:
                task.is_favorite = not task.is_favorite
                session.commit()
        self._load_tasks(self.current_project_id)

    def _refresh_technologies(self) -> None:
        """
        Обновляет список технологий проекта при нажатии на кнопку.
        Показывает предупреждение, если файл requirements.txt не найден
        """

        if self.current_project_id is None:
            QMessageBox.warning(self, 'Нет проекта', 'Сначала выберите проект.')
            return
        with Session(self.engine) as session:
            project = get_project_by_id(session, self.current_project_id)
            if not project:
                return
            req_path = Path(project.path) / 'requirements.txt'
            if not req_path.exists():
                QMessageBox.warning(self, 'Файл не найден', f'requirements.txt не найден в {project.path}')
                return
            new_tech_json = parse_requirements(str(req_path))
            update_project(session, self.current_project_id, technologies=new_tech_json)
            self._show_project_info(self.current_project_id)
            QMessageBox.information(self, 'Готово', 'Технологии обновлены.')

    def _open_in_pycharm(self) -> None:
        """
        Открывает выбранный проект в PyCharm.
        Пока что заглушка todo сделать функционал
        """

        current_item = self.project_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Нет проекта', 'Выберите проект.')
            return
        project_id = current_item.data(0, Qt.ItemDataRole.UserRole)
        with Session(self.engine) as session:
            project = get_project_by_id(session, project_id)
            if project:
                text = (f'Открыть проект "{project.display_name}" в PyCharm\n'
                        f'Путь: {project.path}\n'
                        f'(В стадии разработки)')
                QMessageBox.information(self, 'PyCharm', text)

    def _edit_project_dialog(self) -> None:
        """ Открывает диалог редактирования проекта """

        current_item = self.project_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Нет проекта', 'Выберите проект.')
            return
        project_id = current_item.data(0, Qt.ItemDataRole.UserRole)
        with Session(self.engine) as session:
            project = get_project_by_id(session, project_id)
            if not project:
                return
            dialog = QDialog(self)
            dialog.setWindowTitle(f'Редактировать проект: {project.display_name}')
            layout = QFormLayout(dialog)

            display_name_edit = QLineEdit(project.display_name)
            layout.addRow('Отображаемое имя:', display_name_edit)

            path_layout = QHBoxLayout()
            path_edit = QLineEdit(project.path)
            btn_choose_path = QPushButton('Выбрать папку...')
            path_layout.addWidget(path_edit)
            path_layout.addWidget(btn_choose_path)
            layout.addRow('Путь к проекту:', path_layout)

            description_edit = QPlainTextEdit(project.description)
            layout.addRow('Описание:', description_edit)

            def choose_new_path():
                folder = QFileDialog.getExistingDirectory(dialog, 'Выбрать новую папку проекта')
                if folder:
                    path_edit.setText(folder)
            btn_choose_path.clicked.connect(choose_new_path)

            try:
                techs = json.loads(project.technologies)
                tech_text = ', '.join(techs)
            except json.JSONDecodeError:
                tech_text = ''
                logger.warning(f'Не удалось разобрать технологии проекта {project.id}: {project.technologies}')
                QMessageBox.warning(
                    self,
                    'Ошибка данных',
                    f'Не удалось прочитать список технологий для проекта "{project.display_name}".\n'
                    'Вы можете ввести их заново вручную в поле ниже.'
                )
            except Exception as error:
                tech_text = ''
                logger.warning(f'Не удалось разобрать технологии проекта {project.id}: {project.technologies}.'
                               f'по причине: {error}')

            tech_edit = QPlainTextEdit()
            tech_edit.setPlainText(tech_text)
            tech_edit.setPlaceholderText('Введите технологии (каждая на новой строке или через запятую)')
            layout.addRow('Технологии:', tech_edit)

            button_box = self._create_button_box()
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addRow(button_box)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_display = display_name_edit.text().strip()
                if not new_display:
                    QMessageBox.warning(self, 'Ошибка', 'Имя не может быть пустым.')
                    return
                new_desc = description_edit.toPlainText().strip()
                new_path = path_edit.text().strip()
                if not new_path:
                    QMessageBox.warning(self, 'Ошибка', 'Путь не может быть пустым.')
                    return

                tech_list = []
                for line in tech_edit.toPlainText().splitlines():
                    for item in line.split(','):
                        item = item.strip()
                        if item:
                            tech_list.append(item)
                tech_json = json.dumps(tech_list)
                with Session(self.engine) as session2:
                    update_project(session2, project_id,
                                   display_name=new_display,
                                   description=new_desc,
                                   path=new_path,
                                   technologies=tech_json)
                self._load_projects()
                QMessageBox.information(self, 'Готово', 'Проект обновлён.')

    def _add_tasks_from_template(self):
        if self.current_project_id is None:
            QMessageBox.warning(self, 'Нет проекта', 'Сначала выберите проект в дереве.')
            return

        # Загружаем задачи из JSON
        tasks_path = self._get_default_tasks_path()
        if not tasks_path.exists():
            QMessageBox.warning(self, 'Файл не найден',
                                f'Файл шаблонов не найден по пути:\n{tasks_path}')
            return

        try:
            with open(tasks_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                tasks_list = data.get('tasks', [])
                if not tasks_list:
                    QMessageBox.information(self, 'Нет задач', 'Файл шаблонов пуст.')
                    return
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось прочитать файл:\n{e}')
            return

        dialog = TemplateTasksDialog(tasks_list, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = dialog.get_selected_tasks()
            if not selected:
                QMessageBox.information(self, 'Нет выбора', 'Вы не выбрали ни одной задачи.')
                return

            with Session(self.engine) as session:
                for task_data in selected:
                    # Приводим is_favorite к bool, если есть
                    is_fav = task_data.get('is_favorite', 'False')
                    if isinstance(is_fav, str):
                        is_fav = is_fav.lower() == 'true'
                    add_task(
                        session,
                        project_id=self.current_project_id,
                        title=task_data.get('title', 'Без названия'),
                        description=task_data.get('description', ''),
                        note=task_data.get('note', ''),
                        code_snippet=task_data.get('code_snippet', ''),
                        status=task_data.get('status', 'new'),
                        priority_order=task_data.get('priority_order', 0),
                        is_favorite=is_fav,
                    )
                session.commit()

            self._load_tasks(self.current_project_id)
            QMessageBox.information(self, 'Готово', f'Добавлено {len(selected)} задач.')

    def _on_search_text_changed(self, text: str):
        """Обработчик изменения текста поиска"""
        self.current_search_text = text.strip()
        self._load_projects()

    def keyPressEvent(self, event):
        """Обработка нажатия клавиш на уровне главного окна."""
        if event.key() == Qt.Key_Delete:
            if self.project_tree.hasFocus():
                self._delete_project()
            elif self.task_list.hasFocus():
                self._delete_task()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def _save_right_splitter_state(self):
        if self.right_splitter:
            self.settings.setValue('right_splitter_state', self.right_splitter.saveState())

    def _save_task_fields_splitter_state(self):
        if hasattr(self, 'task_fields_splitter') and self.task_fields_splitter:
            self.settings.setValue('task_fields_splitter_state', self.task_fields_splitter.saveState())

    def closeEvent(self, event):
        self._save_right_splitter_state()
        self._save_task_fields_splitter_state()
        self.settings.setValue('main_window_geometry', self.saveGeometry())
        super().closeEvent(event)


class TemplateTasksDialog(QDialog):
    def __init__(self, tasks_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Выберите шаблонные задачи')
        self.setMinimumWidth(400)
        self.tasks_data = tasks_data
        self.selected_indices = []

        layout = QVBoxLayout(self)

        label = QLabel('Отметьте задачи, которые хотите добавить:')
        layout.addWidget(label)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        for task in self.tasks_data:
            item = QListWidgetItem(task['title'])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText('ОК')
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText('Отмена')
        layout.addWidget(button_box)

    def get_selected_tasks(self):
        """Возвращает список словарей выбранных задач"""
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(self.tasks_data[i])
        return selected


class TemplateManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle('Управление шаблонными задачами')
        self.setMinimumSize(500, 400)

        self.tasks = []

        layout = QVBoxLayout(self)

        # Список
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._edit_task)
        layout.addWidget(self.list_widget)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_add = QPushButton('➕ Добавить')
        btn_add.clicked.connect(self._add_task)
        btn_layout.addWidget(btn_add)

        btn_edit = QPushButton('✏️ Редактировать')
        btn_edit.clicked.connect(self._edit_task)
        btn_layout.addWidget(btn_edit)

        btn_delete = QPushButton('🗑️ Удалить')
        btn_delete.clicked.connect(self._delete_task)
        btn_layout.addWidget(btn_delete)

        btn_layout.addStretch()
        btn_close = QPushButton('Закрыть')
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

        self._load_data()
        self._refresh_list()

    def _load_data(self):
        if self.parent:
            self.tasks = self.parent._load_templates()
        else:
            self.tasks = []

    def _save_data(self):
        if self.parent:
            self.parent._save_templates(self.tasks)

    def _refresh_list(self):
        self.list_widget.clear()
        for task in self.tasks:
            title = task.get('title', 'Без названия')
            self.list_widget.addItem(title)

    def _add_task(self):
        dialog = TemplateTaskEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_task = dialog.get_task_data()
            self.tasks.append(new_task)
            self._save_data()
            self._refresh_list()

    def _edit_task(self):
        current_row = self.list_widget.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, 'Нет выбора', 'Выберите задачу для редактирования.')
            return
        task_data = self.tasks[current_row]
        dialog = TemplateTaskEditDialog(self, task_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated = dialog.get_task_data()
            self.tasks[current_row] = updated
            self._save_data()
            self._refresh_list()

    def _delete_task(self):
        current_row = self.list_widget.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, 'Нет выбора', 'Выберите задачу для удаления.')
            return
        reply = QMessageBox.question(
            self,
            'Удаление',
            'Вы уверены, что хотите удалить эту шаблонную задачу?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            del self.tasks[current_row]
            self._save_data()
            self._refresh_list()

class TemplateTaskEditDialog(QDialog):
    def __init__(self, parent=None, task_data=None):
        super().__init__(parent)
        self.task_data = task_data if task_data else {}
        self.setWindowTitle('Редактирование шаблонной задачи' if task_data else 'Новая шаблонная задача')
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.title_edit = QLineEdit(self.task_data.get('title', ''))
        layout.addRow('Заголовок:', self.title_edit)

        self.desc_edit = QPlainTextEdit(self.task_data.get('description', ''))
        self.desc_edit.setPlaceholderText('Описание задачи...')
        layout.addRow('Описание:', self.desc_edit)

        self.note_edit = QPlainTextEdit(self.task_data.get('note', ''))
        self.note_edit.setPlaceholderText('Заметки...')
        layout.addRow('Заметка:', self.note_edit)

        self.code_edit = QPlainTextEdit(self.task_data.get('code_snippet', ''))
        self.code_edit.setPlaceholderText('Код...')
        layout.addRow('Код:', self.code_edit)

        self.status_combo = QComboBox()
        for display_name, _ in MainWindow.STATUS_CHOICES:
            self.status_combo.addItem(display_name)
            if task_data:
                status_code = task_data.get('status', 'new')
                display_name = MainWindow.status_to_display(status_code)
                idx = self.status_combo.findText(display_name)
                if idx >= 0:
                    self.status_combo.setCurrentIndex(idx)
        layout.addRow('Статус:', self.status_combo)

        self.fav_check = QCheckBox()
        fav_val = self.task_data.get('is_favorite', 'False')
        if isinstance(fav_val, str):
            fav_val = fav_val.lower() == 'true'
        self.fav_check.setChecked(bool(fav_val))
        layout.addRow('Избранное:', self.fav_check)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText('ОК')
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText('Отмена')
        layout.addRow(button_box)

    def get_task_data(self):
        status_display = self.status_combo.currentText()
        status_code = MainWindow.status_to_code(status_display)
        return {
            'title': self.title_edit.text().strip(),
            'description': self.desc_edit.toPlainText().strip(),
            'note': self.note_edit.toPlainText().strip(),
            'code_snippet': self.code_edit.toPlainText().strip(),
            'status': status_code,
            'is_favorite': 'True' if self.fav_check.isChecked() else 'False',
            'priority_order': 0,
        }
