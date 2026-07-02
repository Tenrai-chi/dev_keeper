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

        main_splitter = QSplitter(Qt.Horizontal)
        central_widget.setLayout(QVBoxLayout())
        central_widget.layout().addWidget(main_splitter)

        # ---- Левая панель: проекты ----
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

        btn_add_project = QPushButton("➕ Добавить проект")
        btn_add_project.clicked.connect(self._add_project_dialog)
        left_layout.addWidget(btn_add_project)

        btn_delete_project = QPushButton("🗑️ Удалить проект")
        btn_delete_project.clicked.connect(self._delete_project)
        left_layout.addWidget(btn_delete_project)

        # ---- Правая панель: задачи + заметки ----
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)

        # Список задач
        tasks_label = QLabel("📋 Задачи")
        tasks_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(tasks_label)

        self.task_list = QListWidget()
        self.task_list.itemClicked.connect(self._on_task_selected)
        right_layout.addWidget(self.task_list)

        # Кнопки управления задачами
        task_buttons = QHBoxLayout()
        btn_add_task = QPushButton("➕ Добавить задачу")
        btn_add_task.clicked.connect(self._add_task_dialog)
        btn_archive = QPushButton("📦 В архив")
        btn_archive.clicked.connect(self._archive_task)
        btn_unarchive = QPushButton("↩️ Восстановить")
        btn_unarchive.clicked.connect(self._unarchive_task)
        task_buttons.addWidget(btn_add_task)
        task_buttons.addWidget(btn_archive)
        task_buttons.addWidget(btn_unarchive)
        right_layout.addLayout(task_buttons)

        # Заметки
        note_label = QLabel("📝 Заметка к задаче")
        note_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        right_layout.addWidget(note_label)

        self.note_edit = QTextEdit()
        self.note_edit.setPlaceholderText("Здесь будут заметки по выбранной задаче...")
        right_layout.addWidget(self.note_edit)

        btn_save_note = QPushButton("💾 Сохранить заметку")
        btn_save_note.clicked.connect(self._save_note)
        right_layout.addWidget(btn_save_note)

        # Чекбокс "Показать архивные задачи"
        self.show_archived_check = QCheckBox("Показать архивные задачи")
        self.show_archived_check.stateChanged.connect(self._reload_tasks)
        right_layout.addWidget(self.show_archived_check)

        # Добавляем панели в сплиттер
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([300, 700])

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
                    item.setForeground(Qt.gray)  # архивные задачи серым
                self.task_list.addItem(item)

        self.note_edit.clear()
        self.current_task_id = None

    def _reload_tasks(self):
        if self.current_project_id is not None:
            self._load_tasks(self.current_project_id)

    # ---------- Обработчики выбора ----------
    def _on_project_selected(self, item: QTreeWidgetItem, column: int = 0):
        project_id = item.data(0, Qt.UserRole)
        if project_id is not None:
            self._load_tasks(project_id)

    def _on_task_selected(self, item: QListWidgetItem):
        task_id = item.data(Qt.UserRole)
        if task_id is not None:
            self.current_task_id = task_id
            with Session(self.engine) as session:
                task = get_task_by_id(session, task_id)
                if task:
                    self.note_edit.setPlainText(task.note)

    # ---------- Добавление проекта ----------
    def _add_project_dialog(self):
        """Диалог добавления проекта с выбором папки и парсингом requirements."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить проект")
        layout = QFormLayout(dialog)

        # Поле для отображаемого имени
        display_name_edit = QLineEdit()
        layout.addRow("Отображаемое имя:", display_name_edit)

        # Выбор папки
        path_label = QLabel("Папка не выбрана")
        btn_choose = QPushButton("Выбрать папку...")
        chosen_path = [None]  # замыкание

        def choose_folder():
            folder = QFileDialog.getExistingDirectory(dialog, "Выбрать папку проекта")
            if folder:
                chosen_path[0] = folder
                path_label.setText(folder)
                # автоматически предлагаем tech_name из имени папки
                tech_name = Path(folder).name
                if not display_name_edit.text():
                    display_name_edit.setText(tech_name)

        btn_choose.clicked.connect(choose_folder)
        layout.addRow("Путь к проекту:", btn_choose)
        layout.addRow("", path_label)

        # Техническое имя (можно оставить автоматическим)
        tech_name_edit = QLineEdit()
        tech_name_edit.setPlaceholderText("будет взято из имени папки")
        layout.addRow("Техническое имя (опционально):", tech_name_edit)

        # Описание
        description_edit = QPlainTextEdit()
        description_edit.setPlaceholderText("Краткое описание проекта...")
        layout.addRow("Описание:", description_edit)

        # Кнопки
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

            # Парсим requirements
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
                # Добавляем базовые задачи (шаблон)
                self._add_default_tasks(session, project.id)

            self._load_projects()
            QMessageBox.information(self, "Готово", f"Проект '{display_name}' добавлен.")

    def _add_default_tasks(self, session, project_id):
        """Добавляет стандартные задачи для нового проекта."""
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
                from crud import delete_project
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

    #---------- Сохранение заметки ----------
    def _save_note(self):
        if self.current_task_id is None:
            QMessageBox.warning(self, "Нет задачи", "Выберите задачу, чтобы сохранить заметку.")
            return
        new_note = self.note_edit.toPlainText()
        with Session(self.engine) as session:
            update_task(session, self.current_task_id, note=new_note)
        QMessageBox.information(self, "Сохранено", "Заметка обновлена.")

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
        """Восстанавливает задачу из архива (снимает флаг is_archived)."""
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