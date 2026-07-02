from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select

from database import Project, Task


# ---------- CRUD-функции для проектов ----------
def get_all_projects(session: Session) -> list[Project]:
    """Возвращает все проекты, отсортированные по display_name."""
    stmt = select(Project).order_by(Project.display_name)
    return list(session.execute(stmt).scalars().all())


def get_project_by_id(session: Session, project_id: int) -> Project | None:
    """Возвращает проект по ID или None."""
    return session.get(Project, project_id)


# ---------- CRUD-функции для задач ----------
def get_tasks_by_project(session: Session, project_id: int, include_archived: bool = False) -> list[Task]:
    """
    Возвращает задачи проекта, отсортированные по priority_order.
    Если include_archived=False, возвращает только активные задачи.
    """

    stmt = select(Task).where(Task.project_id == project_id)
    if not include_archived:
        stmt = stmt.where(Task.is_archived == False)
    stmt = stmt.order_by(Task.priority_order)
    return list(session.execute(stmt).scalars().all())


def get_task_by_id(session: Session, task_id: int) -> Task | None:
    """Возвращает задачу по ID или None """

    return session.get(Task, task_id)

def add_project(
    session: Session,
    tech_name: str,
    display_name: str,
    path: str,
    description: str = "",
    technologies: str = "[]"
) -> Project:
    """Добавляет новый проект."""
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
    """Удаляет проект и все его задачи."""
    project = session.get(Project, project_id)
    if not project:
        return False
    session.delete(project)
    session.commit()
    return True


def add_task(
    session: Session,
    project_id: int,
    title: str,
    description: str = "",
    note: str = "",
    code_snippet: str = "",
    parent_id: int | None = None,
    priority_order: int | None = None
) -> Task:
    """Добавляет новую задачу в проект."""
    if priority_order is None:
        # Определяем максимальный priority_order для активных задач
        count = session.query(Task).filter(
            Task.project_id == project_id,
            Task.is_archived == False
        ).count()
        priority_order = count  # новая задача встаёт в конец

    task = Task(
        project_id=project_id,
        parent_id=parent_id,
        title=title,
        description=description,
        note=note,
        code_snippet=code_snippet,
        priority_order=priority_order
    )
    session.add(task)
    session.commit()
    return task


def update_task(session: Session, task_id: int, **kwargs) -> Task | None:
    """
    Обновляет поля задачи.
    Допустимые ключи: title, description, note, code_snippet,
    parent_id, is_archived, completed_at, priority_order.
    """
    task = session.get(Task, task_id)
    if not task:
        return None
    for key, value in kwargs.items():
        if hasattr(task, key):
            setattr(task, key, value)
    session.commit()
    return task


def archive_task(session: Session, task_id: int) -> Task | None:
    """Перемещает задачу в архив."""
    task = session.get(Task, task_id)
    if not task:
        return None
    task.is_archived = True
    task.completed_at = datetime.now()
    session.commit()
    return task


def reorder_tasks(session: Session, project_id: int, task_ids_in_order: list[int]) -> None:
    """Обновляет priority_order для списка задач (для drag-and-drop)."""
    for index, task_id in enumerate(task_ids_in_order):
        task = session.get(Task, task_id)
        if task and task.project_id == project_id:
            task.priority_order = index
    session.commit()
