import os
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
    QTextEdit, QPushButton, QSplitter, QLabel, QMessageBox,
    QFileDialog, QDialog, QLineEdit, QPlainTextEdit, QComboBox,
    QDialogButtonBox, QFormLayout, QCheckBox
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session

from database import init_db, parse_requirements
from crud import (
    get_all_projects, get_project_by_id,
    get_tasks_by_project, get_task_by_id,
    add_project, add_task, update_task, archive_task,
    update_project, delete_project
)
from test_data import add_test_data


class MainWindow(QMainWindow):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.current_project_id = None
        self.current_task_id = None

        self.setWindowTitle("DevKeeper — Управление проектами")
        self.setMinimumSize(1000, 700)

        self._setup_ui()
        self._load_projects()

    # ---------- Сборка интерфейса ----------
    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Главный горизонтальный сплиттер: левая панель | правая панель
        main_splitter = QSplitter(Qt.Horizontal)
        central_widget.setLayout(QVBoxLayout())
        central_widget.layout().addWidget(main_splitter)

        # ---------- Левая панель: проекты ----------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)

        left_label = QLabel("📁 Проекты")
        left_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(left_label)

        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderHidden(True)
        self.project_tree.setIndentation(15)
        self.project_tree.itemClicked.connect(self._on_project_selected)
        left_layout.addWidget(self.project_tree)

        # Кнопки управления проектами
        btn_add_project = QPushButton("➕ Добавить")
        btn_add_project.clicked.connect(self._add_project_dialog)
        left_layout.addWidget(btn_add_project)

        btn_delete_project = QPushButton("🗑️ Удалить")
        btn_delete_project.clicked.connect(self._delete_project)
        left_layout.addWidget(btn_delete_project)

        btn_open_pycharm = QPushButton("🚀 Открыть в PyCharm")
        btn_open_pycharm.clicked.connect(self._open_in_pycharm)
        left_layout.addWidget(btn_open_pycharm)

        btn_edit_project = QPushButton("✏️ Редактировать проект")
        btn_edit_project.clicked.connect(self._edit_project_dialog)
        left_layout.addWidget(btn_edit_project)

        left_layout.addStretch()

        # ---------- Правая панель: задачи + детали ----------
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)

        # Верхняя часть: список задач
        header_layout = QHBoxLayout()
        tasks_label = QLabel("📋 Задачи")
        tasks_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(tasks_label)
        header_layout.addStretch()
        self.show_archived_check = QCheckBox("Показать архивные")
        self.show_archived_check.stateChanged.connect(self._reload_tasks)
        header_layout.addWidget(self.show_archived_check)
        right_layout.addLayout(header_layout)

        self.task_list = QListWidget()
        self.task_list.itemClicked.connect(self._on_task_selected)
        right_layout.addWidget(self.task_list)

        # Кнопки управления задачами
        task_buttons = QHBoxLayout()
        btn_add_task = QPushButton("➕ Добавить задачу")
        btn_add_task.clicked.connect(self._add_task_dialog)
        task_buttons.addWidget(btn_add_task)

        btn_archive = QPushButton("📦 В архив")
        btn_archive.clicked.connect(self._archive_task)
        task_buttons.addWidget(btn_archive)

        btn_unarchive = QPushButton("↩️ Восстановить")
        btn_unarchive.clicked.connect(self._unarchive_task)
        task_buttons.addWidget(btn_unarchive)

        right_layout.addLayout(task_buttons)

        # Разделитель
        line = QLabel()
        line.setFrameStyle(QLabel.HLine)
        right_layout.addWidget(line)

        # Нижняя часть: детали задачи (редактируемые)
        detail_label = QLabel("📝 Детали задачи")
        detail_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(detail_label)

        # Заголовок
        right_layout.addWidget(QLabel("Заголовок:"))
        self.detail_title = QLineEdit()
        self.detail_title.setPlaceholderText("Заголовок задачи")
        right_layout.addWidget(self.detail_title)

        # Описание
        right_layout.addWidget(QLabel("Описание:"))
        self.detail_description = QTextEdit()
        self.detail_description.setPlaceholderText("Описание задачи...")
        self.detail_description.setMaximumHeight(80)
        right_layout.addWidget(self.detail_description)

        # Заметка
        right_layout.addWidget(QLabel("Заметка:"))
        self.detail_note = QTextEdit()
        self.detail_note.setPlaceholderText("Заметки, идеи, ссылки...")
        self.detail_note.setMaximumHeight(80)
        right_layout.addWidget(self.detail_note)

        # Код
        right_layout.addWidget(QLabel("Код:"))
        self.detail_code = QTextEdit()
        self.detail_code.setPlaceholderText("Сниппет кода...")
        self.detail_code.setFontFamily("Courier New")
        self.detail_code.setMaximumHeight(100)
        right_layout.addWidget(self.detail_code)

        # Статус и кнопка сохранения
        status_save_layout = QHBoxLayout()
        self.detail_status = QLabel("Статус: не выбрано")
        status_save_layout.addWidget(self.detail_status)
        status_save_layout.addStretch()

        btn_save = QPushButton("💾 Сохранить изменения")
        btn_save.clicked.connect(self._save_task_details)
        status_save_layout.addWidget(btn_save)

        right_layout.addLayout(status_save_layout)

        # Добавляем панели в сплиттер
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([300, 700])

        # По умолчанию очищаем детали
        self._clear_details()

    # ---------- Загрузка данных ----------
    def _load_projects(self):
        self.project_tree.clear()
        with Session(self.engine) as session:
            projects = get_all_projects(session)
            for project in projects:
                item = QTreeWidgetItem([project.display_name])
                item.setData(0, Qt.UserRole, project.id)
                self.project_tree.addTopLevelItem(item)

        if self.project_tree.topLevelItemCount() > 0:
            self.project_tree.setCurrentItem(self.project_tree.topLevelItem(0))
            self._on_project_selected(self.project_tree.topLevelItem(0))

    def _load_tasks(self, project_id: int):
        self.task_list.clear()
        self.current_project_id = project_id
        include_archived = self.show_archived_check.isChecked()
        with Session(self.engine) as session:
            tasks = get_tasks_by_project(session, project_id, include_archived=include_archived)
            for task in tasks:
                item = QListWidgetItem(task.title)
                item.setData(Qt.UserRole, task.id)
                if task.is_archived:
                    item.setForeground(Qt.gray)
                self.task_list.addItem(item)
        # Очищаем детали, так как проект переключился
        self._clear_details()
        self.current_task_id = None

    def _reload_tasks(self):
        if self.current_project_id is not None:
            self._load_tasks(self.current_project_id)

    # ---------- Обработчики выбора ----------
    def _on_project_selected(self, item: QTreeWidgetItem, column: int = 0):
        project_id = item.data(0, Qt.UserRole)
        if project_id is not None:
            self._load_tasks(project_id)
            # Показываем информацию о проекте в деталях (только для чтения)
            self._show_project_info(project_id)

    def _on_task_selected(self, item: QListWidgetItem):
        task_id = item.data(Qt.UserRole)
        if task_id is not None:
            self.current_task_id = task_id
            self._show_task_info(task_id)

    # ---------- Отображение информации в панели деталей ----------
    def _show_project_info(self, project_id: int):
        """Заполняет панель деталей информацией о проекте (только чтение)."""
        with Session(self.engine) as session:
            project = get_project_by_id(session, project_id)
            if project:
                self.detail_title.setText(f"[ПРОЕКТ] {project.display_name}")
                self.detail_description.setPlainText(project.description)
                self.detail_note.setPlainText(f"Техническое имя: {project.tech_name}\nПуть: {project.path}")
                try:
                    techs = json.loads(project.technologies)
                    self.detail_code.setPlainText("Технологии: " + ", ".join(techs))
                except:
                    self.detail_code.setPlainText("Технологии: (не указаны)")
                self.detail_status.setText("Статус: проект (только чтение)")
                # Делаем поля только для чтения
                self.detail_title.setReadOnly(True)
                self.detail_description.setReadOnly(True)
                self.detail_note.setReadOnly(True)
                self.detail_code.setReadOnly(True)

    def _show_task_info(self, task_id: int):
        """Заполняет панель деталей данными задачи (редактируемые)."""
        with Session(self.engine) as session:
            task = get_task_by_id(session, task_id)
            if task:
                self.detail_title.setText(task.title)
                self.detail_description.setPlainText(task.description)
                self.detail_note.setPlainText(task.note)
                self.detail_code.setPlainText(task.code_snippet)
                status = "архивна" if task.is_archived else "активна"
                self.detail_status.setText(f"Статус: {status} (ID: {task.id})")
                # Включаем редактирование
                self.detail_title.setReadOnly(False)
                self.detail_description.setReadOnly(False)
                self.detail_note.setReadOnly(False)
                self.detail_code.setReadOnly(False)

    def _clear_details(self):
        """Очищает панель деталей."""
        self.detail_title.clear()
        self.detail_description.clear()
        self.detail_note.clear()
        self.detail_code.clear()
        self.detail_status.setText("Статус: не выбрано")
        self.detail_title.setReadOnly(True)
        self.detail_description.setReadOnly(True)
        self.detail_note.setReadOnly(True)
        self.detail_code.setReadOnly(True)

    # ---------- Сохранение задачи ----------
    def _save_task_details(self):
        if self.current_task_id is None:
            QMessageBox.warning(self, "Нет задачи", "Выберите задачу для редактирования.")
            return
        with Session(self.engine) as session:
            task = get_task_by_id(session, self.current_task_id)
            if task:
                task.title = self.detail_title.text()
                task.description = self.detail_description.toPlainText()
                task.note = self.detail_note.toPlainText()
                task.code_snippet = self.detail_code.toPlainText()
                session.commit()
                # Обновляем список задач (чтобы обновить заголовок)
                self._load_tasks(self.current_project_id)
                QMessageBox.information(self, "Сохранено", "Изменения сохранены.")

    # ---------- Добавление проекта ----------
    def _add_project_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить проект")
        layout = QFormLayout(dialog)

        display_name_edit = QLineEdit()
        layout.addRow("Отображаемое имя:", display_name_edit)

        path_label = QLabel("Папка не выбрана")
        btn_choose = QPushButton("Выбрать папку...")
        chosen_path = [None]

        def choose_folder():
            folder = QFileDialog.getExistingDirectory(dialog, "Выбрать папку проекта")
            if folder:
                chosen_path[0] = folder
                path_label.setText(folder)
                tech_name = Path(folder).name
                if not display_name_edit.text():
                    display_name_edit.setText(tech_name)

        btn_choose.clicked.connect(choose_folder)
        layout.addRow("Путь к проекту:", btn_choose)
        layout.addRow("", path_label)

        tech_name_edit = QLineEdit()
        tech_name_edit.setPlaceholderText("будет взято из имени папки")
        layout.addRow("Техническое имя (опционально):", tech_name_edit)

        description_edit = QPlainTextEdit()
        description_edit.setPlaceholderText("Краткое описание проекта...")
        layout.addRow("Описание:", description_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.Accepted:
            if not chosen_path[0]:
                QMessageBox.warning(self, "Ошибка", "Выберите папку проекта.")
                return
            display_name = display_name_edit.text().strip()
            if not display_name:
                QMessageBox.warning(self, "Ошибка", "Введите отображаемое имя.")
                return

            tech_name = tech_name_edit.text().strip()
            if not tech_name:
                tech_name = Path(chosen_path[0]).name

            description = description_edit.toPlainText().strip()

            req_path = Path(chosen_path[0]) / "requirements.txt"
            tech_json = parse_requirements(str(req_path)) if req_path.exists() else "[]"

            with Session(self.engine) as session:
                project = add_project(
                    session,
                    tech_name=tech_name,
                    display_name=display_name,
                    path=chosen_path[0],
                    description=description,
                    technologies=tech_json
                )
                self._add_default_tasks(session, project.id)

            self._load_projects()
            QMessageBox.information(self, "Готово", f"Проект '{display_name}' добавлен.")

    def _add_default_tasks(self, session, project_id):
        default_tasks = [
            {"title": "📄 Написать README.md", "description": "Описание проекта, установка, примеры"},
            {"title": "⚙️ Настроить .gitignore", "description": "Добавить стандартные исключения"},
            {"title": "🐳 Написать Dockerfile / docker-compose", "description": "Контейнеризация проекта"},
            {"title": "📦 Создать виртуальное окружение", "description": "Установить зависимости"},
        ]
        for i, task_data in enumerate(default_tasks):
            add_task(
                session,
                project_id=project_id,
                title=task_data["title"],
                description=task_data["description"],
                priority_order=i
            )
        session.commit()

    # ---------- Удаление проекта ----------
    def _delete_project(self):
        current_item = self.project_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Нет проекта", "Выберите проект для удаления.")
            return
        project_id = current_item.data(0, Qt.UserRole)
        if not project_id:
            return
        reply = QMessageBox.question(
            self,
            "Удаление проекта",
            "Вы уверены, что хотите удалить проект и все его задачи?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            with Session(self.engine) as session:
                delete_project(session, project_id)
            self._load_projects()
            QMessageBox.information(self, "Удалено", "Проект удалён.")

    # ---------- Добавление задачи ----------
    def _add_task_dialog(self):
        if self.current_project_id is None:
            QMessageBox.warning(self, "Нет проекта", "Сначала выберите проект в дереве.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить задачу")
        layout = QFormLayout(dialog)

        title_edit = QLineEdit()
        layout.addRow("Заголовок:", title_edit)

        description_edit = QPlainTextEdit()
        description_edit.setPlaceholderText("Описание задачи...")
        layout.addRow("Описание:", description_edit)

        note_edit = QPlainTextEdit()
        note_edit.setPlaceholderText("Заметки, идеи, ссылки...")
        layout.addRow("Заметка:", note_edit)

        code_edit = QPlainTextEdit()
        code_edit.setPlaceholderText("Сниппет кода (если есть)...")
        layout.addRow("Код:", code_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.Accepted:
            title = title_edit.text().strip()
            if not title:
                QMessageBox.warning(self, "Ошибка", "Введите заголовок задачи.")
                return

            with Session(self.engine) as session:
                add_task(
                    session,
                    project_id=self.current_project_id,
                    title=title,
                    description=description_edit.toPlainText().strip(),
                    note=note_edit.toPlainText().strip(),
                    code_snippet=code_edit.toPlainText().strip()
                )
            self._load_tasks(self.current_project_id)

    # ---------- Архивация / восстановление ----------
    def _archive_task(self):
        current_item = self.task_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Нет задачи", "Выберите задачу для архивации.")
            return
        task_id = current_item.data(Qt.UserRole)
        with Session(self.engine) as session:
            archive_task(session, task_id)
        self._load_tasks(self.current_project_id)

    def _unarchive_task(self):
        current_item = self.task_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Нет задачи", "Выберите задачу для восстановления.")
            return
        task_id = current_item.data(Qt.UserRole)
        with Session(self.engine) as session:
            task = get_task_by_id(session, task_id)
            if task:
                update_task(session, task_id, is_archived=False, completed_at=None)
        self._load_tasks(self.current_project_id)

    # ---------- Заглушки для новых кнопок ----------
    def _open_in_pycharm(self):
        current_item = self.project_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Нет проекта", "Выберите проект.")
            return
        project_id = current_item.data(0, Qt.UserRole)
        with Session(self.engine) as session:
            project = get_project_by_id(session, project_id)
            if project:
                QMessageBox.information(self, "PyCharm", f"Открыть проект '{project.display_name}' в PyCharm\nПуть: {project.path}\n(Функция будет реализована позже)")

    def _edit_project_dialog(self):
        current_item = self.project_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Нет проекта", "Выберите проект.")
            return
        project_id = current_item.data(0, Qt.UserRole)
        with Session(self.engine) as session:
            project = get_project_by_id(session, project_id)
            if not project:
                return
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Редактировать проект: {project.display_name}")
            layout = QFormLayout(dialog)

            display_name_edit = QLineEdit(project.display_name)
            layout.addRow("Отображаемое имя:", display_name_edit)

            description_edit = QPlainTextEdit(project.description)
            layout.addRow("Описание:", description_edit)

            # Технологии — показываем как текстовое поле (можно будет вводить через запятую)
            try:
                techs = json.loads(project.technologies)
                tech_text = ", ".join(techs)
            except:
                tech_text = ""
            tech_edit = QLineEdit(tech_text)
            tech_edit.setPlaceholderText("Введите технологии через запятую")
            layout.addRow("Технологии:", tech_edit)

            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addRow(buttons)

            if dialog.exec() == QDialog.Accepted:
                new_display = display_name_edit.text().strip()
                if not new_display:
                    QMessageBox.warning(self, "Ошибка", "Имя не может быть пустым.")
                    return
                new_desc = description_edit.toPlainText().strip()
                # Парсим технологии
                tech_list = [t.strip() for t in tech_edit.text().split(",") if t.strip()]
                tech_json = json.dumps(tech_list)
                with Session(self.engine) as session2:
                    update_project(session2, project_id, display_name=new_display, description=new_desc, technologies=tech_json)
                self._load_projects()
                QMessageBox.information(self, "Готово", "Проект обновлён.")