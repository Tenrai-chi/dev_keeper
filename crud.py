from datetime import datetime

from PySide6.QtWidgets import QListWidgetItem
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from database import Project, Task
import logging
logger = logging.getLogger(__name__)


# ---------- CRUD-функции для проектов ----------
def get_all_projects(session: Session) -> list[Project]:
    stmt = select(Project).order_by(
        Project.is_favorite.desc(),
        Project.display_name
    )
    return list(session.execute(stmt).scalars().all())


def get_project_by_id(session: Session, project_id: int) -> Project | None:
    return session.get(Project, project_id)


def add_project(
    session: Session,
    tech_name: str,
    display_name: str,
    path: str,
    description: str = "",
    technologies: str = "[]"
) -> Project:
    project = Project(
        tech_name=tech_name,
        display_name=display_name,
        path=path,
        description=description,
        technologies=technologies
    )
    session.add(project)
    session.commit()
    return project


def delete_project(session: Session, project_id: int) -> bool:
    project = session.get(Project, project_id)
    if not project:
        return False
    session.delete(project)
    session.commit()
    return True


def update_project(session: Session, project_id: int, **kwargs) -> Project | None:
    project = session.get(Project, project_id)
    if not project:
        return None
    for key, value in kwargs.items():
        if hasattr(project, key):
            setattr(project, key, value)
    session.commit()
    return project


def toggle_favorite(session: Session, project_id: int) -> Project | None:
    project = session.get(Project, project_id)
    if not project:
        return None
    project.is_favorite = not project.is_favorite
    session.commit()
    return project


# ---------- CRUD-функции для задач ----------
def get_tasks_by_project(session: Session, project_id: int, include_archived: bool = False) -> list[Task]:
    stmt = select(Task).where(Task.project_id == project_id)
    if not include_archived:
        stmt = stmt.where(Task.status != 'archived')
    stmt = stmt.order_by(
        Task.is_favorite.desc(),
        Task.priority_order
    )
    return list(session.execute(stmt).scalars().all())


def get_task_by_id(session: Session, task_id: int) -> Task | None:
    return session.get(Task, task_id)


def add_task(
    session: Session,
    project_id: int,
    title: str,
    description: str = "",
    note: str = "",
    code_snippet: str = "",
    parent_id: int | None = None,
    priority_order: int | None = None,
    status: str = "new",
    is_favorite: bool = False
) -> Task:
    if priority_order is None:
        count = session.query(Task).filter(
            Task.project_id == project_id,
            Task.status != 'archived'
        ).count()
        priority_order = count
    task = Task(
        project_id=project_id,
        parent_id=parent_id,
        title=title,
        description=description,
        note=note,
        code_snippet=code_snippet,
        priority_order=priority_order,
        status=status,
        is_favorite=is_favorite
    )
    session.add(task)
    session.commit()
    return task


def update_task(session: Session, task_id: int, **kwargs) -> Task | None:
    task = session.get(Task, task_id)
    if not task:
        return None
    for key, value in kwargs.items():
        if hasattr(task, key):
            setattr(task, key, value)
    session.commit()
    return task


def delete_task(session: Session, task_id: int) -> bool:
    task = session.get(Task, task_id)
    if not task:
        return False
    session.delete(task)
    session.commit()
    return True


def archive_task(session: Session, task_id: int) -> Task | None:
    task = session.get(Task, task_id)
    if not task:
        return None
    task.status = 'archived'
    task.completed_at = datetime.now()
    session.commit()
    return task


def unarchive_task(session: Session, task_id: int) -> Task | None:
    task = session.get(Task, task_id)
    if not task:
        return None
    if task.status == 'archived':
        task.status = 'done'   # или 'new' – выбери подходящий
        task.completed_at = None
        session.commit()
    return task


def change_task_status(session: Session, task_id: int, new_status: str) -> Task | None:
    task = session.get(Task, task_id)
    if not task:
        return None
    task.status = new_status
    if new_status in ('done', 'archived'):
        task.completed_at = datetime.now()
    else:
        task.completed_at = None
    session.commit()
    return task


def reorder_tasks(session: Session, project_id: int, task_ids_in_order: list[int]) -> None:
    for index, task_id in enumerate(task_ids_in_order):
        task = session.get(Task, task_id)
        if task and task.project_id == project_id:
            task.priority_order = index
    session.commit()


def search_projects(session: Session, search_text: str) -> list[Project]:
    """
    Возвращает проекты, у которых display_name или technologies
    содержат search_text (без учёта регистра).
    Если search_text пустой, возвращает все проекты.
    """

    if not search_text or not search_text.strip():
        return get_all_projects(session)

    search_lower = search_text.lower()
    all_projects = get_all_projects(session)
    result = []
    for project in all_projects:
        if (search_lower in project.display_name.lower() or
                search_lower in project.technologies.lower()):
            result.append(project)
    return result