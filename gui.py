import json
import logging
import subprocess

from pathlib import Path
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QListWidget,
    QTextEdit, QPushButton, QSplitter, QLabel, QMessageBox,
    QFileDialog, QDialog, QLineEdit, QPlainTextEdit,
    QDialogButtonBox, QFormLayout, QCheckBox, QComboBox,
    QStackedWidget, QApplication, QListWidgetItem
)
from sqlalchemy.orm import Session

from crud import (
    get_all_projects, get_project_by_id, add_project, delete_project,
    update_project, toggle_favorite, get_tasks_by_project,
    get_task_by_id, add_task, update_task,
    change_task_status, search_projects, update_parent_status,
    archive_subtree, unarchive_subtree, delete_task_with_children
)
from utils import (
    parse_requirements, status_to_display, status_to_code,
    get_default_tasks_path, STATUS_CHOICES, load_templates, save_templates
)
from help_content import get_help_html
from themes import get_dark_theme, get_light_theme


logger = logging.getLogger(__name__)
program_version = '1.0'


class MainWindow(QMainWindow):
    """ Главное рабочее окно приложения. """

    def __init__(self, engine):
        """ Инициализирует главное окно, загружает сохраненную тему и настраивает интерфейс """

        super().__init__()
        self.engine = engine
        self.current_project_id = None
        self.current_task_id = None
        self.settings = QSettings('DevKeeper', 'Settings')
        self.current_theme = self.settings.value('theme', 'system', type=str)
        self.current_search_text = ''
        self.right_splitter = None
        self.task_fields_splitter = None

        self.setWindowTitle(f'DevKeeper v{program_version}')
        self.setMinimumSize(1000, 700)
        geometry = self.settings.value('main_window_geometry')
        if geometry is not None:
            self.restoreGeometry(geometry)

        self._setup_menu()
        self._setup_ui()
        self._apply_theme(str(self.current_theme))
        self._load_projects()

    # -------- Настройка интерфейса --------
    def _setup_menu(self) -> None:
        """ Создает главное меню с пунктами "Настройки" и "Справка" """

        menubar = self.menuBar()

        settings_menu = menubar.addMenu('⚙️ Настройки')

        action_general = QAction('Общие', self)
        action_general.triggered.connect(self._open_settings_dialog)
        settings_menu.addAction(action_general)

        action_templates = QAction('Управление шаблонами задач...', self)
        action_templates.triggered.connect(self._open_template_manager)
        settings_menu.addAction(action_templates)

        # Меню Справка
        help_menu = menubar.addMenu('❓ Справка')
        action_help = QAction('Руководство пользователя', self)
        action_help.triggered.connect(self._show_help)
        help_menu.addAction(action_help)

        action_about = QAction('О программе', self)
        action_about.triggered.connect(self._show_about)
        help_menu.addAction(action_about)

    def _open_template_manager(self):
        """ Открывает диалог управления шаблонными задачами. """

        dialog = TemplateManagerDialog(self)
        dialog.exec()

    def _apply_theme(self, theme_name: str) -> None:
        """
        Применяет выбранную тему оформления и сохраняет ее в настройках.
        Args:
            theme_name: параметр стиля dark, light или system
        """

        self.current_theme = theme_name
        if theme_name == 'system':
            if QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
                theme_name = 'dark'
            else:
                theme_name = 'light'
        if theme_name == 'dark':
            self.setStyleSheet(get_dark_theme())
        else:
            self.setStyleSheet(get_light_theme())
        self.settings.setValue('theme', self.current_theme)

    def _setup_ui(self) -> None:
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

    def _create_left_panel(self) -> QWidget:
        """
        Создает левую панель с деревом проектов и кнопками управления.
        Returns:
            QWidget: панель проектов.
        """

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

        self.btn_open_pycharm = QPushButton('🚀 Открыть в PyCharm')  # <-- исправлено имя
        self.btn_open_pycharm.clicked.connect(self._open_in_pycharm)
        btn_layout.addWidget(self.btn_open_pycharm)

        btn_edit = QPushButton('✏️ Редактировать')
        btn_edit.clicked.connect(self._edit_project_dialog)
        btn_layout.addWidget(btn_edit)

        layout.addLayout(btn_layout)
        self._update_pycharm_button_visibility()  # теперь будет работать
        return widget

    def _create_right_panel(self) -> QWidget:
        """
        Создает правую панель, которая содержит:
            - Список задач (дерево).
            - Кнопки управления.
            - Списание проекта / задач.
        Returns:
            QWidget: панель задач и дополнительной информации проектов и задач.
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

        btn_add_multiple = QPushButton('📋 Подзадачи')
        btn_add_multiple.clicked.connect(self._add_multiple_tasks_dialog)
        header_layout.addWidget(btn_add_multiple)

        layout.addLayout(header_layout)

        self.task_tree = QTreeWidget()
        self.task_tree.setHeaderHidden(True)
        self.task_tree.setIndentation(20)
        self.task_tree.setColumnCount(1)
        self.task_tree.itemClicked.connect(self._on_task_tree_clicked)
        self.task_tree.itemDoubleClicked.connect(self._toggle_task_favorite)
        layout.addWidget(self.task_tree)

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
        top_layout.addWidget(self.task_tree)
        top_layout.addLayout(task_btn_layout)

        self.details_stack = QStackedWidget()
        self.details_stack.addWidget(self._create_task_details_panel())
        self.details_stack.addWidget(self._create_project_details_panel())

        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addWidget(self.details_stack)

        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.addWidget(top_widget)
        self.right_splitter.addWidget(bottom_widget)
        self.right_splitter.setStretchFactor(0, 1)  # верх – 1 часть
        self.right_splitter.setStretchFactor(1, 2)  # низ – 2 части
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

    def _create_task_details_panel(self) -> QWidget:
        """
        Создает панель редактирования и просмотра деталей задачи.
        Returns:
            QWidget: панель деталей задачи.
        """

        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel('Заголовок:'))
        self.detail_title = QLineEdit()
        layout.addWidget(self.detail_title)

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

        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel('Статус:'))
        self.status_combo = QComboBox()
        for display_name, _ in STATUS_CHOICES:
            self.status_combo.addItem(display_name)
        status_layout.addWidget(self.status_combo)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        btn_save = QPushButton('💾 Сохранить изменения')
        btn_save.clicked.connect(self._save_task_details)
        layout.addWidget(btn_save)

        state = self.settings.value('task_fields_splitter_state')
        if state is not None:
            fields_splitter.restoreState(state)
        else:
            fields_splitter.setSizes([150, 150, 300])

        fields_splitter.splitterMoved.connect(self._save_task_fields_splitter_state)

        self.task_fields_splitter = fields_splitter

        return widget

    def _create_project_details_panel(self) -> QWidget:
        """
        Создает панель просмотра деталей проекта для чтения.
        Returns:
            QWidget: панель деталей проекта.
        """

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

    # -------- Методы загрузки данных --------
    def _load_projects(self) -> None:
        """
        Загружает все проекты и выводит в дереве проектов.
        Если задан поисковый запрос, применяется фильтр.
        """

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

    def _load_tasks(self, project_id: int) -> None:
        """
        Загружает задачи выбранного проекта и строит иерархическое дерево.
        Args:
            project_id: ID проекта.
        """

        self.task_tree.clear()
        self.current_project_id = project_id
        include_archived = self.show_archived_check.isChecked()
        with Session(self.engine) as session:
            tasks = get_tasks_by_project(session, project_id, include_archived=include_archived)
            items_map = {}

            for task in tasks:
                item = QTreeWidgetItem()
                item.setData(0, Qt.ItemDataRole.UserRole, task.id)
                star = '⭐ ' if task.is_favorite else ''
                status_display = status_to_display(task.status)
                text = f'{star}{task.title} [{status_display}]'
                item.setText(0, text)  # теперь текст в колонке 0
                self._set_item_color(item, task.status)
                items_map[task.id] = item

            for task in tasks:
                item = items_map[task.id]
                if task.parent_id is not None and task.parent_id in items_map:
                    parent_item = items_map[task.parent_id]
                    parent_item.addChild(item)
                else:
                    self.task_tree.addTopLevelItem(item)

            self.task_tree.expandAll()

        self._clear_details()
        self.current_task_id = None

    def _reload_tasks(self) -> None:
        """ Перезагружает список задач при изменении флага "Показать архивные" """

        if self.current_project_id is not None:
            self._load_tasks(self.current_project_id)

    # -------- Методы обработки выбора --------
    def _on_project_selected(self, item: QTreeWidgetItem, column: int = 0):
        """
        Обработчик клика по проекту в дереве проектов.
        Args:
            item: объект выбранного элемента.
            column: номер колонки.
        """

        project_id = item.data(column, Qt.ItemDataRole.UserRole)
        if project_id is not None:
            self._load_tasks(project_id)
            self._show_project_info(project_id)

    def _on_task_tree_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """
        Обработчик клика по элементу в дереве задач.
        При клике на текст открывает детали задачи.
        Args:
            item: выбранный элемент.
            column: номер колонки.
        """
        if column == 0:
            task_id = item.data(0, Qt.ItemDataRole.UserRole)
            if task_id is not None:
                self.current_task_id = task_id
                self._show_task_info(task_id)

    # -------- Методы отображения деталей --------
    def _show_project_info(self, project_id: int) -> None:
        """
        отображает информацию о проекте в панели деталей проекта.
        Args:
            project_id: ID проекта.
        """

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

    def _show_task_info(self, task_id: int) -> None:
        """
        Отображает информацию о задаче в панели редактирования задачи.
        Args:
            task_id: ID задачи.
        """

        self.details_stack.setCurrentIndex(0)
        with Session(self.engine) as session:
            task = get_task_by_id(session, task_id)
            if task:
                self.detail_title.setText(task.title)
                self.detail_description.setPlainText(task.description)
                self.detail_note.setPlainText(task.note)
                self.detail_code.setPlainText(task.code_snippet)
                display_name = status_to_display(task.status)
                idx = self.status_combo.findText(display_name)
                if idx >= 0:
                    self.status_combo.setCurrentIndex(idx)
                self.detail_title.setReadOnly(False)
                self.detail_description.setReadOnly(False)
                self.detail_note.setReadOnly(False)
                self.detail_code.setReadOnly(False)
                self.status_combo.setEnabled(True)

    def _clear_details(self) -> None:
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

    # -------- Методы изменения данных --------
    def _save_task_details(self) -> None:
        """
        Сохраняет изменения в текущей задаче из панели редактирования.
        Обновляет поля, статус и родительскую задачу при наличии.
        """

        if self.current_task_id is None:
            QMessageBox.warning(self, 'Нет задачи', 'Выберите задачу для редактирования.')
            return
        with Session(self.engine) as session:
            update_task(session, self.current_task_id,
                        title=self.detail_title.text(),
                        description=self.detail_description.toPlainText(),
                        note=self.detail_note.toPlainText(),
                        code_snippet=self.detail_code.toPlainText())
            # Обновляем статус, если изменился
            new_status_display = self.status_combo.currentText()
            new_status = status_to_code(new_status_display)
            task = get_task_by_id(session, self.current_task_id)
            if task and task.status != new_status:
                change_task_status(session, self.current_task_id, new_status)
            # Обновляем родителя
            if task and task.parent_id:
                logger.info(
                    f"Вызов update_parent_status для parent_id={task.parent_id} (сохранение задачи), id={task.id}")
                update_parent_status(session, task.parent_id)
            self._load_tasks(self.current_project_id)

    def _add_project_dialog(self) -> None:
        """
        Открывает диалог добавления нового проекта.
        Позволяет указать имя, путь (опционально) и описания.
        Если указан путь проекта, то пытается обработать файл requirements.txt.
        """

        dialog = QDialog(self)
        dialog.setWindowTitle('Добавить проект')
        layout = QFormLayout(dialog)

        display_name_edit = QLineEdit()
        layout.addRow('Отображаемое имя:', display_name_edit)

        path_label = QLabel('Папка не выбрана')
        btn_choose = QPushButton('Выбрать папку...')
        selected_path = None

        def choose_folder():
            nonlocal selected_path
            folder = QFileDialog.getExistingDirectory(dialog, 'Выбрать папку проекта')
            if folder:
                selected_path = folder
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
            display_name = display_name_edit.text().strip()
            if not display_name:
                QMessageBox.warning(self, 'Ошибка', 'Введите отображаемое имя.')
                return

            # Если путь не выбран, остаётся None
            tech_name = tech_name_edit.text().strip()
            if not tech_name and selected_path:
                tech_name = Path(selected_path).name
            elif not tech_name:
                tech_name = ''

            description = description_edit.toPlainText().strip()

            # Если путь выбран, пробуем парсить requirements
            tech_json = '[]'
            if selected_path:
                req_path = Path(selected_path) / 'requirements.txt'
                if req_path.exists():
                    tech_json = parse_requirements(str(req_path))
                    if tech_json is None:
                        tech_json = '[]'
                        QMessageBox.warning(
                            self,
                            'Предупреждение',
                            'Не удалось прочитать файл requirements.txt.\n'
                            'Технологии не будут добавлены. Вы сможете добавить их позже вручную.'
                        )
                else:
                    pass
            else:
                pass

            with Session(self.engine) as session:
                project_data = {
                    'tech_name': tech_name,
                    'display_name': display_name,
                    'path': selected_path if selected_path else '',
                    'description': description,
                    'technologies': tech_json,
                }
                add_project(session=session, project_data=project_data)

            self._load_projects()
            QMessageBox.information(self, 'Готово', f'Проект "{display_name}" добавлен.')

    def _add_task_dialog(self) -> None:
        """
        Открывает диалог добавления новой задачи в текущий проект.
        Позволяет указать заголовок, описание, заметку, код и родительскую задачу.
        """

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

        # Выбор родительской задачи
        parent_combo = QComboBox()
        parent_combo.addItem('(нет родителя)', None)
        with Session(self.engine) as session:
            tasks = get_tasks_by_project(session, self.current_project_id, include_archived=True)
            for task in tasks:
                parent_combo.addItem(f'{task.title} (ID {task.id})', task.id)
        layout.addRow('Родительская задача:', parent_combo)

        button_box = self._create_button_box()
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            title = title_edit.text().strip()
            if not title:
                QMessageBox.warning(self, 'Ошибка', 'Введите заголовок задачи.')
                return

            parent_id = parent_combo.currentData()
            with Session(self.engine) as session:
                task_data = {
                    'project_id': self.current_project_id,
                    'title': title,
                    'description': description_edit.toPlainText().strip(),
                    'note': note_edit.toPlainText().strip(),
                    'code_snippet': code_edit.toPlainText().strip(),
                    'status': 'new',
                    'parent_id': parent_id,
                }
                add_task(session=session, task_data=task_data)
            if parent_id:
                logger.info(f"Вызов update_parent_status для parent_id={parent_id} (множественное создание)")
                update_parent_status(session, parent_id)
            self._load_tasks(self.current_project_id)

    def _add_multiple_tasks_dialog(self) -> None:
        """
        Диалог создания нескольких задач одновременно.
        Задачи вводятся построчно в формате "- Заголовок. Описание".
        Можно указать родительскую задачу.
        """

        if self.current_project_id is None:
            QMessageBox.warning(self, 'Нет проекта', 'Сначала выберите проект.')
            return

        current_item = self.task_tree.currentItem()
        default_parent_id = None
        if current_item:
            default_parent_id = current_item.data(0, Qt.ItemDataRole.UserRole)

        dialog = QDialog(self)
        dialog.setWindowTitle('Множественное создание задач')
        layout = QVBoxLayout(dialog)

        instructions = QLabel(
            'Введите задачи в формате:\n'
            '- Заголовок. Описание (опционально)\n'
            'Каждая задача с новой строки, начинается с "-".'
        )
        layout.addWidget(instructions)

        text_edit = QPlainTextEdit()
        text_edit.setPlaceholderText('- Написать документацию. Описать все API\n- Настроить CI/CD\n- Создать тесты')
        layout.addWidget(text_edit)

        # Выбор родителя (опционально)
        parent_layout = QHBoxLayout()
        parent_layout.addWidget(QLabel('Создать как подзадачи для:'))
        parent_combo = QComboBox()
        parent_combo.addItem('(проект, без родителя)', None)
        default_index = 0
        with Session(self.engine) as session:
            tasks = get_tasks_by_project(session, self.current_project_id, include_archived=True)
            for idx, task in enumerate(tasks, start=1):
                parent_combo.addItem(f'{task.title}', task.id)
                if task.id == default_parent_id:
                    default_index = idx
        parent_combo.setCurrentIndex(default_index)
        parent_layout.addWidget(parent_combo)
        layout.addLayout(parent_layout)

        button_box = self._create_button_box()
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = text_edit.toPlainText().strip()
            if not text:
                QMessageBox.warning(self, 'Ошибка', 'Введите хотя бы одну задачу.')
                return
            lines = text.splitlines()
            tasks_to_create = []
            for line in lines:
                line = line.strip()
                if not line.startswith('-'):
                    continue

                content = line[1:].strip()
                if not content:
                    continue
                parts = content.split('.', 1)
                title = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else ''
                if not title:
                    continue
                tasks_to_create.append((title, description))

            if not tasks_to_create:
                QMessageBox.warning(self, 'Ошибка', 'Не найдено задач для добавления.')
                return

            parent_id = parent_combo.currentData()
            with Session(self.engine) as session:
                for title, description in tasks_to_create:
                    task_data = {
                        'project_id': self.current_project_id,
                        'title': title,
                        'description': description,
                        'status': 'new',
                        'parent_id': parent_id,
                    }
                    add_task(session=session, task_data=task_data)
                session.commit()
            if parent_id:
                update_parent_status(session, parent_id)
            self._load_tasks(self.current_project_id)
            QMessageBox.information(self, 'Готово', f'Добавлено {len(tasks_to_create)} задач.')

    def _delete_project(self) -> None:
        """ Удаляет выбранный проект после подтверждения пользователя """

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

    def _delete_task(self) -> None:
        """
        Удаляет выбранную задачу после подтверждения.
            Если у задачи есть подзадачи, предлагает удалить только ее или всю ветку.
        """

        current_item = self.task_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Нет задачи', 'Выберите задачу для удаления.')
            return
        task_id = current_item.data(0, Qt.ItemDataRole.UserRole)
        if task_id is None:
            return

        child_count = current_item.childCount()
        if child_count > 0:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Удаление задачи')
            msg_box.setText('У этой задачи есть подзадачи. Что вы хотите сделать?')
            btn_only = QPushButton('Только эту задачу')
            btn_with_children = QPushButton('С подзадачами')
            btn_cancel = QPushButton('Отмена')
            msg_box.addButton(btn_only, QMessageBox.ButtonRole.YesRole)
            msg_box.addButton(btn_with_children, QMessageBox.ButtonRole.NoRole)
            msg_box.addButton(btn_cancel, QMessageBox.ButtonRole.RejectRole)
            msg_box.setDefaultButton(btn_cancel)
            reply = msg_box.exec()
            if reply == QMessageBox.ButtonRole.RejectRole:
                return
            with Session(self.engine) as session:
                if reply == QMessageBox.ButtonRole.YesRole:
                    delete_task_with_children(session, task_id, delete_children=False)
                else:
                    delete_task_with_children(session, task_id, delete_children=True)
            self._load_tasks(self.current_project_id)
            QMessageBox.information(self, 'Удалено', 'Задача удалена.')
        else:
            reply = self._question_dialog('Удаление задачи', 'Вы уверены, что хотите удалить эту задачу?')
            if reply == QMessageBox.StandardButton.Yes:
                with Session(self.engine) as session:
                    delete_task_with_children(session, task_id, delete_children=False)
                self._load_tasks(self.current_project_id)
                QMessageBox.information(self, 'Удалено', 'Задача удалена.')

    def _archive_task(self) -> None:
        """
        Архивирует выбранную задачу и все ее подзадачи (рекурсивно).
        Устанавливает статус archived/
        """

        current_item = self.task_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Нет задачи', 'Выберите задачу для архивации.')
            return
        task_id = current_item.data(0, Qt.ItemDataRole.UserRole)
        if task_id is None:
            return

        with Session(self.engine) as session:
            count = archive_subtree(session, task_id)
            # Обновляем родителя (если есть)
            task = get_task_by_id(session, task_id)
            if task and task.parent_id:
                update_parent_status(session, task.parent_id)

        self._load_tasks(self.current_project_id)
        QMessageBox.information(self, 'Архивация', f'Задача и её подзадачи ({count}) архивированы.')

    def _unarchive_task(self) -> None:
        """
        Восстанавливает выбранную архивную задачу и все ее подзадачи (рекурсивно).
        Устанавливает статус done для всех.
        """

        current_item = self.task_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Нет задачи', 'Выберите задачу для восстановления.')
            return
        task_id = current_item.data(0, Qt.ItemDataRole.UserRole)
        if task_id is None:
            return

        with Session(self.engine) as session:
            count = unarchive_subtree(session, task_id)
            # Обновляем родителя
            task = get_task_by_id(session, task_id)
            if task and task.parent_id:
                update_parent_status(session, task.parent_id)

        self._load_tasks(self.current_project_id)
        QMessageBox.information(self, 'Восстановление', f'Задача и её подзадачи ({count}) восстановлены.')

    def _toggle_favorite(self, item: QTreeWidgetItem, column: int = None) -> None:
        """
        Переключает статус избранного у выбранного проекта (по двойному клику).
        Args:
            item: элемент проекта.
            column: номер колонки.
        """

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

    def _toggle_task_favorite(self, item: QListWidgetItem) -> None:
        """
        Переключает статус избранного у выбранной задачи (по двойному клику).
        Args:
            item: элемент задачи.
        """

        task_id = item.data(0, Qt.ItemDataRole.UserRole)
        if task_id is None:
            return
        with Session(self.engine) as session:
            task = get_task_by_id(session, task_id)
            if task:
                update_task(session, task_id, is_favorite=not task.is_favorite)
        self._load_tasks(self.current_project_id)

    def _refresh_technologies(self) -> None:
        """
        Обновляет список технологий путем повторной обработки файлы.
        Показывает предупреждение, если файл requirements.txt не найден.
        """

        if self.current_project_id is None:
            QMessageBox.warning(self, 'Нет проекта', 'Сначала выберите проект.')
            return
        with Session(self.engine) as session:
            project = get_project_by_id(session, self.current_project_id)
            if not project:
                return
            if not project.path.strip():
                QMessageBox.warning(self, 'Нет пути',
                                    'У проекта не указан путь к папке. Невозможно обновить технологии.')
                return
            req_path = Path(project.path) / 'requirements.txt'
            if not req_path.exists():
                QMessageBox.warning(self, 'Файл не найден', f'requirements.txt не найден в {project.path}')
                return
            new_tech_json = parse_requirements(str(req_path))
            update_project(session, self.current_project_id, technologies=new_tech_json)
            self._show_project_info(self.current_project_id)
            QMessageBox.information(self, 'Готово', 'Технологии обновлены.')

    def _edit_project_dialog(self) -> None:
        """
        открывает диалог редактирования проекта.
        Позволяет изменить имя, описание, путь и технологии.
        """

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
            path_edit.setPlaceholderText('Если проект локальный')
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

    def _add_tasks_from_template(self) -> None:
        """ Открывает диалог выбора шаблонных задач для добавления в текущий проект. """

        if self.current_project_id is None:
            QMessageBox.warning(self, 'Нет проекта', 'Сначала выберите проект в дереве.')
            return

        # Загружаем задачи из JSON
        tasks_path = get_default_tasks_path()
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
                    is_fav = task_data.get('is_favorite', 'False')
                    if isinstance(is_fav, str):
                        is_fav = is_fav.lower() == 'true'
                    task_data = {
                        'project_id': self.current_project_id,
                        'title': task_data.get('title', 'Без названия'),
                        'description': task_data.get('description', ''),
                        'note': task_data.get('note', ''),
                        'code_snippet': task_data.get('code_snippet', ''),
                        'status': task_data.get('status', 'new'),
                        'priority_order': task_data.get('priority_order', 0),
                        'is_favorite': is_fav,
                    }
                    add_task(session=session, task_data=task_data)
                session.commit()

            self._load_tasks(self.current_project_id)
            QMessageBox.information(self, 'Готово', f'Добавлено {len(selected)} задач.')


    # -------- Настройки и справка --------
    def _open_settings_dialog(self) -> None:
        """ Открывает диалог общих настроек. """

        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            theme, use_pycharm, pycharm_path = dialog.get_settings()
            self.settings.setValue('theme', theme)
            self.settings.setValue('use_pycharm', use_pycharm)
            self.settings.setValue('pycharm_path', pycharm_path)
            self._apply_theme(theme)
            self._update_pycharm_button_visibility()

    def _show_about(self) -> None:
        """ Показывает окно «О программе» с информацией о версии и авторе. """

        text = (f'DevKeeper v{program_version}\n\n'
                f'Приложение для управления проектами и задачами.\n\n'
                f'Создатель: Tenrai\n'
                f'2026 г.'
                )
        QMessageBox.information(self, 'О программе', text)

    def _update_pycharm_button_visibility(self) -> None:
        """ Обновляет видимость кнопки "Открыть в PyCharm" в зависимости от настроек. """

        if hasattr(self, 'btn_open_pycharm'):
            use_pycharm = self.settings.value('use_pycharm', False, type=bool)
            self.btn_open_pycharm.setVisible(use_pycharm)

    def _show_help(self) -> None:
        """ Открывает окно с кратким руководством пользователя. """

        dialog = HelpDialog(self)
        dialog.exec()

    # -------- Вспомогательные методы --------
    def _set_item_color(self, item: QTreeWidgetItem, status: str) -> None:
        """
        Устанавливает цвет текста задачи в зависимости от ее статуса.
        Args:
            item: элемент дерева.
            status: код статуса new, in_progress, done, archived

        Returns:
        """

        if status == 'archived':
            item.setForeground(0, Qt.GlobalColor.gray)
        elif status == 'done':
            item.setForeground(0, Qt.GlobalColor.darkGreen)
        elif status == 'in_progress':
            item.setForeground(0, Qt.GlobalColor.darkBlue)
        else:  # new или fallback
            item.setForeground(0, Qt.GlobalColor.black if self.current_theme != 'dark' else Qt.GlobalColor.white)

    def _update_task_item_in_tree(self, task_id: int, task) -> None:
        """
        Обновляет текст и цвет элемента дерева для задачи по ее ID.
        Args:
            task_id: ID задачи.
            task: объект задачи с обновлёнными данными.
        """

        def find_item(root_item):
            if root_item.data(0, Qt.ItemDataRole.UserRole) == task_id:
                return root_item
            for child_ind in range(root_item.childCount()):
                found = find_item(root_item.child(child_ind))
                if found:
                    return found
            return None

        for item_ind in range(self.task_tree.topLevelItemCount()):
            item = find_item(self.task_tree.topLevelItem(item_ind))
            if item:
                star = '⭐ ' if task.is_favorite else ''
                status_display = status_to_display(task.status)
                item.setText(0, f'{star}{task.title} [{status_display}]')
                self._set_item_color(item, task.status)
                break

    def _save_right_splitter_state(self) -> None:
        """ Сохраняет состояние сплиттера полей задачи в настройках. """

        if self.right_splitter:
            self.settings.setValue('right_splitter_state', self.right_splitter.saveState())

    def _save_task_fields_splitter_state(self) -> None:
        """ Сохраняет состояние сплиттера полей задачи в настройках. """

        if hasattr(self, 'task_fields_splitter') and self.task_fields_splitter:
            self.settings.setValue('task_fields_splitter_state', self.task_fields_splitter.saveState())

    def _on_search_text_changed(self, text: str) -> None:
        """
        Обработчик изменения текста в поле поиска проектов.
        Args:
            text: текущий текст поиска.
        """

        self.current_search_text = text.strip()
        self._load_projects()

    def _open_in_pycharm(self) -> None:
        """
        Открывает выбранный проект в PyCharm.
        Использует путь, указанный в настройках.
        Показывает предупреждение, если путь не указан или проект не привязан к папке.
        """

        current_item = self.project_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Нет проекта', 'Выберите проект.')
            return
        project_id = current_item.data(0, Qt.ItemDataRole.UserRole)
        with Session(self.engine) as session:
            project = get_project_by_id(session, project_id)
            if project:
                if not project.path.strip():
                    QMessageBox.warning(self, 'Нет пути', f'Проект "{project.display_name}" не привязан к папке.')
                    return
                pycharm_path = self.settings.value('pycharm_path', '').strip()
                if not pycharm_path:
                    QMessageBox.warning(self, 'Путь не указан', 'Не указан путь к PyCharm в настройках.')
                    return
                try:
                    subprocess.Popen([pycharm_path, project.path])
                except Exception as e:
                    QMessageBox.critical(self, 'Ошибка', f'Не удалось открыть PyCharm:\n{e}')

    def keyPressEvent(self, event) -> None:
        """
        Обрабатывает нажатия на клавише на уровне главного окна.
        Комбинации:
            - Delete - удалить выбранный проект или задачу.
            - Ctrl+P - открыть диалог добавления проекта.
            - Ctrl+T - открыть диалог добавления задачи.
            - Ctrl+= (Ctrl++) - развернуть все задачи.
            - Ctrl+- - свернуть все задачи.
        """

        ctrl = event.modifiers() & Qt.KeyboardModifier.ControlModifier

        # DEL
        if event.key() == Qt.Key.Key_Delete:
            if self.project_tree.hasFocus():
                self._delete_project()
            elif self.task_tree.hasFocus():
                self._delete_task()
            else:
                super().keyPressEvent(event)
            return

        # Ctrl+P – новый проект
        if ctrl and event.key() == Qt.Key.Key_P:
            self._add_project_dialog()
            return

        # Ctrl+T – новая задача
        if ctrl and event.key() == Qt.Key.Key_T:
            self._add_task_dialog()
            return

        # Ctrl++ – развернуть все
        if ctrl and event.key() == Qt.Key.Key_Equal:
            self.task_tree.expandAll()
            return

        # Ctrl+- – свернуть все
        if ctrl and event.key() == Qt.Key.Key_Minus:
            self.task_tree.collapseAll()
            return

        # Остальное – стандартная обработка
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        """ Сохраняет состояние интерфейса при закрытии окна. """

        self._save_right_splitter_state()
        self._save_task_fields_splitter_state()
        self.settings.setValue('main_window_geometry', self.saveGeometry())
        super().closeEvent(event)

    def _question_dialog(self, title: str, text: str) -> int:
        """
        Показывает диалог с вопросом и кнопками "Да" и "Нет".
        Args:
            title: заголовок диалога.
            text: текст вопроса.

        Returns:
            int: QMessageBox.YesRole или QMessageBox.NoRole.
        """

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.button(QMessageBox.StandardButton.Yes).setText('Да')
        msg_box.button(QMessageBox.StandardButton.No).setText('Нет')
        msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
        return msg_box.exec()

    # -------- Статические методы --------
    @staticmethod
    def _create_button_box() -> QDialogButtonBox:
        """
        Создаёт кнопки ОК и Отмена с русскими подписями.

        Returns:
            QDialogButtonBox: готовый блок кнопок.
        """

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText('ОК')
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText('Отмена')
        return button_box


class TemplateTasksDialog(QDialog):
    """ Диалог выбора шаблонных задач для добавления. """

    def __init__(self, tasks_data, parent=None):
        """
        Инициирует диалог со списком шаблонных задач.

        Args:
            tasks_data: список словарей с данными задач.
            parent: родительское окно.
        """

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

    def get_selected_tasks(self) -> list[dict]:
        """
        Возвращает список выбранных задач.
        Returns:
            list[dict]: список словарей выбранных задач.
        """

        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(self.tasks_data[i])
        return selected


class TemplateManagerDialog(QDialog):
    """ Диалог управления шаблонными задачами (добавление, редактирование, удаление) """

    def __init__(self, parent=None):
        """
        Инициализирует диалог управления шаблонами.
        Args:
            parent: родительское окно.
        """

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

    def _load_data(self) -> None:
        """ Загружает список шаблонов из родительского окна. """

        if self.parent:
            self.tasks = load_templates()
        else:
            self.tasks = []

    def _save_data(self) -> None:
        """ Сохраняет список шаблонов через родительское окно. """

        if self.parent:
            success, error = save_templates(self.tasks)
            if not success:
                QMessageBox.critical(self, 'Ошибка', f'Не удалось сохранить шаблоны:\n{error}')

    def _refresh_list(self) -> None:
        """ Обновляет отображение списка шаблонов. """

        self.list_widget.clear()
        for task in self.tasks:
            title = task.get('title', 'Без названия')
            self.list_widget.addItem(title)

    def _add_task(self) -> None:
        """ Открывает диалог добавления нового шаблона задачи. """

        dialog = TemplateTaskEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_task = dialog.get_task_data()
            self.tasks.append(new_task)
            self._save_data()
            self._refresh_list()

    def _edit_task(self) -> None:
        """ Открывает диалог редактирования выбранного шаблона. """

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

    def _delete_task(self) -> None:
        """ Удаляет выбранный шаблон после подтверждения. """

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
    """ Диалог редактирования или создания шаблонной задачи. """

    def __init__(self, parent=None, task_data=None):
        """
        Инициализирует диалог с данными задачи.
        Args:
            parent: родительское окно.
            task_data: данные задачи для редактирования.
        """

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
        for display_name, _ in STATUS_CHOICES:
            self.status_combo.addItem(display_name)
            if task_data:
                status_code = task_data.get('status', 'new')
                display_name = status_to_display(status_code)
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

    def get_task_data(self) -> dict:
        """
        Возвращает данные задачи из полей диалога.
        Returns:
             dict: словарь с данными задачи.
        """
        status_display = self.status_combo.currentText()
        status_code = status_to_code(status_display)
        return {
            'title': self.title_edit.text().strip(),
            'description': self.desc_edit.toPlainText().strip(),
            'note': self.note_edit.toPlainText().strip(),
            'code_snippet': self.code_edit.toPlainText().strip(),
            'status': status_code,
            'is_favorite': 'True' if self.fav_check.isChecked() else 'False',
        }


class SettingsDialog(QDialog):
    """ Диалог общих настроек (тема, путь к PyCharm). """

    def __init__(self, parent=None):
        """
        Инициализирует диалог настроек.
        Args:
            parent: родительское окно.
        """

        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle('Настройки')
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Тема
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel('Тема:'))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['Светлая', 'Тёмная', 'Системная'])
        current_theme = parent.settings.value('theme', 'system')
        index_map = {'light': 0, 'dark': 1, 'system': 2}
        self.theme_combo.setCurrentIndex(index_map.get(current_theme, 2))
        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)

        # Чекбокс использования PyCharm
        self.use_pycharm_check = QCheckBox('Использовать PyCharm для открытия проектов')
        use_pycharm = parent.settings.value('use_pycharm', False, type=bool)
        self.use_pycharm_check.setChecked(use_pycharm)
        layout.addWidget(self.use_pycharm_check)

        # Виджет-контейнер для пути к PyCharm (можно скрывать/показывать)
        self.pycharm_container = QWidget()
        pycharm_layout = QHBoxLayout(self.pycharm_container)
        pycharm_layout.setContentsMargins(0, 0, 0, 0)

        self.pycharm_path_edit = QLineEdit()
        pycharm_path = parent.settings.value('pycharm_path', '')
        self.pycharm_path_edit.setText(pycharm_path)
        self.pycharm_path_edit.setPlaceholderText('Путь к исполняемому файлу PyCharm')
        pycharm_layout.addWidget(self.pycharm_path_edit)

        btn_browse = QPushButton('Обзор...')
        btn_browse.clicked.connect(self._browse_pycharm)
        pycharm_layout.addWidget(btn_browse)

        # По умолчанию скрываем/показываем в зависимости от чекбокса
        self.pycharm_container.setVisible(use_pycharm)
        layout.addWidget(self.pycharm_container)

        # Связываем чекбокс с видимостью контейнера
        self.use_pycharm_check.toggled.connect(self.pycharm_container.setVisible)

        # Кнопки ОК/Отмена
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText('ОК')
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText('Отмена')
        layout.addWidget(button_box)

    def _browse_pycharm(self) -> None:
        """ Открывает диалог выбора исполняемого файла PyCharm. """

        file_path, _ = QFileDialog.getOpenFileName(self, 'Выбрать исполняемый файл PyCharm',
                                                   '', 'Executable (*.exe);;All Files (*.*)')
        if file_path:
            self.pycharm_path_edit.setText(file_path)

    def get_settings(self) -> tuple:
        """
        Возвращает выбранные настройки.

        Returns:
            tuple: (тема, использовать ли PyCharm, путь к PyCharm).
        """

        theme_index = self.theme_combo.currentIndex()
        index_map = {0: 'light', 1: 'dark', 2: 'system'}
        theme = index_map.get(theme_index, 'system')
        use_pycharm = self.use_pycharm_check.isChecked()
        pycharm_path = self.pycharm_path_edit.text().strip()
        return theme, use_pycharm, pycharm_path


class HelpDialog(QDialog):
    """ Диалог с руководством пользователя. """

    def __init__(self, parent=None):
        """
        Инициализирует диалог справки.

        Args:
            parent (QWidget, optional): родительское окно.
    """

        super().__init__(parent)
        self.setWindowTitle('Руководство пользователя')
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        title = QLabel('📖 Краткое руководство по работе с DevKeeper')
        title.setStyleSheet('font-size: 16px; font-weight: bold; margin: 10px 0;')
        layout.addWidget(title)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml(get_help_html(program_version))
        layout.addWidget(text)

        # Кнопка закрытия
        btn_close = QPushButton('Закрыть')
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)
