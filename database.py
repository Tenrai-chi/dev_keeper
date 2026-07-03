import json
import logging
import re

from datetime import datetime
from typing import Optional, List

from sqlalchemy import create_engine, text, String, Text, Boolean, DateTime, Integer, ForeignKey, Engine
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()
logger = logging.getLogger(__name__)


class Project(Base):
    """
    Таблица с данными о проектах
    """
    __tablename__ = 'projects'

    id: Mapped[int] = mapped_column(primary_key=True)
    tech_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, default='')
    technologies: Mapped[str] = mapped_column(Text, default='[]')
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    tasks: Mapped[List['Task']] = relationship(
        'Task',
        back_populates='project',
        cascade='all, delete-orphan',
        order_by='Task.priority_order'
    )

    def __repr__(self):
        return f'<Проект {self.display_name}>'


class Task(Base):
    """
    Таблица с задачами проектов
    """
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'))
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey('tasks.id', ondelete='CASCADE'), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default='')
    note: Mapped[str] = mapped_column(Text, default='')
    code_snippet: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(20), default='new')  # new, in_progress, review, done, archived
    priority_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)

    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    parent: Mapped[Optional["Task"]] = relationship("Task", remote_side=[id], backref="subtasks")

    def __repr__(self):
        return f'<Задачи {self.title}>'


def init_db(db_path: str = 'projects.db') -> Engine:
    """
    Создаёт и настраивает движок SQLite.
    Создаёт таблицы, если их нет.
    Возвращает движок (engine).
    """

    engine = create_engine(
        f'sqlite:///{db_path}',
        connect_args={
            'check_same_thread': False,
            'timeout': 2.0
        },
        echo=False
    )

    # Применяем PRAGMA для производительности
    with engine.connect() as conn:
        conn.execute(text('PRAGMA journal_mode=WAL'))
        conn.execute(text('PRAGMA synchronous=NORMAL'))
        conn.commit()

    # Создаём таблицы (если не существуют)
    Base.metadata.create_all(engine)
    return engine


def parse_requirements(file_path: str) -> str | None:
    """
    Парсит requirements.txt и возвращает JSON-список библиотек.
    Если файл не найден, возвращает '[]'.
    """

    libraries = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Берём имя пакета до первого символа сравнения
                    pkg = re.split(r'[>=<~!]', line)[0].strip()
                    if pkg:
                        libraries.append(pkg)
    except FileNotFoundError:
        logger.error(f'Файл requirements не найден')
        return None
    except Exception as error:
        logger.error(f'Непредвиденная ошибка парсинга файла requirements: {error}')
        return None

    return json.dumps(libraries)
