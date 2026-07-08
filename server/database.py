import logging

from datetime import datetime
from typing import Optional, List

from sqlalchemy import create_engine, text, String, Text, Boolean, DateTime, ForeignKey, Engine
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship, sessionmaker

from server.config import settings

Base = declarative_base()
logger = logging.getLogger(__name__)


class Users(Base):
    """ Таблица пользователей. Хранит минимум информации. Не требует авторизации """

    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Project(Base):
    """ Таблица с данными о проектах. """

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
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)

    tasks: Mapped[List['Task']] = relationship(
        'Task',
        back_populates='project',
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f'<Проект {self.display_name}>'


class Task(Base):
    """ Таблица с задачами проектов. """

    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'))
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey('tasks.id', ondelete='CASCADE'), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default='')
    note: Mapped[str] = mapped_column(Text, default='')
    code_snippet: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(20), default='new')  # new, in_progress, done, archived
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)

    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    parent: Mapped[Optional["Task"]] = relationship("Task", remote_side=[id], backref="subtasks")

    def __repr__(self):
        return f'<Задачи {self.title}>'


def init_db(db_path: str = 'network_projects.db') -> Engine:
    """
    Создаёт и настраивает движок SQLite.
    Создаёт таблицы, если их нет.

    Args:
        db_path: путь к бд.

    Returns:
        Engine: движок (engine)
    """

    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={
            'check_same_thread': False,
            'timeout': 2.0
        },
        echo=False
    )

    # Применяем PRAGMA для производительности
    with engine.connect() as conn:
        conn.execute(text('PRAGMA foreign_keys = ON'))
        conn.execute(text('PRAGMA journal_mode=WAL'))
        conn.execute(text('PRAGMA synchronous=NORMAL'))
        conn.commit()

    Base.metadata.create_all(engine)
    return engine


engine = init_db()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
