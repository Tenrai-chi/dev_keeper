import json
import re
from datetime import datetime
from typing import Optional, List

from sqlalchemy import create_engine, text, String, Text, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class Project(Base):
    __tablename__ = 'projects'

    id: Mapped[int] = mapped_column(primary_key=True)
    tech_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, default='')
    technologies: Mapped[str] = mapped_column(Text, default='[]')   # JSON-список

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    tasks: Mapped[List['Task']] = relationship(
        'Task',
        back_populates='project',
        cascade='all, delete-orphan',
        order_by='Task.priority_order'
    )

    def __repr__(self):
        return f'<Project {self.display_name}>'


class Task(Base):
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'))
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey('tasks.id', ondelete='CASCADE'), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default='')
    note: Mapped[str] = mapped_column(Text, default='')
    code_snippet: Mapped[str] = mapped_column(Text, default='')

    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    priority_order: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    project: Mapped['Project'] = relationship('Project', back_populates='tasks')
    parent: Mapped[Optional['Task']] = relationship('Task', remote_side=[id], backref='subtasks')

    def __repr__(self):
        return f'<Task {self.title}>'


def init_db(db_path: str = 'projects.db'):
    """
    Создаёт движок SQLite с нужными настройками (WAL, синхронизация)
    и создаёт таблицы, если их нет.
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


def parse_requirements(file_path: str) -> str:
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
        pass
    except Exception as e:
        print(f'Ошибка парсинга requirements: {e}')
    return json.dumps(libraries)
