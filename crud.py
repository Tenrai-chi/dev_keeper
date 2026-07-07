import logging

from datetime import datetime
from sqlalchemy import select, case
from sqlalchemy.orm import Session

from database import Project, Task


logger = logging.getLogger(__name__)


# -------- Работа с проектами --------
def get_all_projects(session: Session) -> list[Project]:
    """
    Возвращает список всех проектов, отсортированных по избранному и имени.
    Args:
        session (Session): сессия SQLAlchemy.

    Returns:
        list[Project]: список проектов.
    """

    stmt_projects = (
        select(Project)
        .order_by(
            Project.is_favorite.desc(),
            Project.display_name
        )
    )
    projects = list(session.execute(stmt_projects).scalars().all())
    return projects


def get_project_by_id(session: Session, project_id: int) -> Project | None:
    """
    Возвращает проект по его ID.
    Args:
        session (Session): сессия SQLAlchemy.
        project_id (int): ID проекта.

    Returns:
        Optional[Project]: объект проекта или None.
    """

    project = session.get(Project, project_id)
    return project


def add_project(session: Session, project_data: dict) -> Project:
    """
    Добавляет новый проект в базу данных.
    Args:
        - session: сессия SQLAlchemy.
        - project_data: словарь с данными для создания проекта.

    Returns:
        - Project: объект созданного проекта.
    """

    project = Project(
        tech_name=project_data.get('tech_name'),
        display_name=project_data.get('display_name'),
        path=project_data.get('path'),
        description=project_data.get('description') or '',
        technologies=project_data.get('technologies') or '[]'
    )
    session.add(project)
    session.commit()
    return project


def delete_project(session: Session, project_id: int) -> bool:
    """
    Удаляет проект по его ID.
    Args:
        session: сессия SQLAlchemy.
        project_id: ID проекта.

    Returns:
        bool: True, если проект был удален, иначе False
    """

    project = session.get(Project, project_id)
    if not project:
        return False
    session.delete(project)
    session.commit()
    return True


def update_project(session: Session, project_id: int, **kwargs) -> Project | None:
    """
    Обновляет поля проекта.
    Args:
        session: сессия SQLAlchemy.
        project_id: ID проекта.
        **kwargs: произвольные именованные аргументы для обновления полей.

    Returns:
        Optional[Project]: обновлённый объект проекта или None, если проект не найден.
    """

    project = session.get(Project, project_id)
    if not project:
        return None
    for key, value in kwargs.items():
        if hasattr(project, key):
            setattr(project, key, value)
    session.commit()
    return project


def toggle_favorite(session: Session, project_id: int) -> Project | None:
    """
    Переключает статус избранного у проекта.
    Args:
        session: сессия SQLAlchemy.
        project_id: ID проекта.

    Returns:
        Optional[Project]: обновленный объект проекта ии None, если проект не найден.
    """

    project = session.get(Project, project_id)
    if not project:
        return None
    project.is_favorite = not project.is_favorite
    session.commit()
    return project


def search_projects(session: Session, search_text: str) -> list[Project]:
    """
    Поиск проектов по названию или технологиям (без учета регистра).
    При пустой строке поиска возвращает все проекты.
    Args:
        session: сессия SQLAlchemy
        search_text: текст для поиска

    Returns:
        list[Project]: список проектов, удовлетворяющих поиску.
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


# -------- Работа с задачами --------
def get_tasks_by_project(session: Session, project_id: int, include_archived: bool = False) -> list[Task]:
    """
    Возвращает отсортированные задачи выбранного проекта.
    Сортировка по флагу избранного и приоритету и стадии.
    Args:
        session: сессия SQLAlchemy.
        project_id: ID проекта.
        include_archived: включать ли архивные задачи. По умолчанию False.

    Returns:
        list[Task]: список отсортированных задач.
    """

    status_order = {
        'in_progress': 0,
        'new': 1,
        'done': 2,
        'archived': 3
    }

    stmt_tasks = select(Task).where(Task.project_id == project_id)
    if not include_archived:
        stmt_tasks = stmt_tasks.where(Task.status != 'archived')

    status_priority = case(
        status_order,
        value=Task.status
    )
    stmt_tasks = stmt_tasks.order_by(
        status_priority,
        Task.is_favorite.desc(),
    )
    tasks = list(session.execute(stmt_tasks).scalars().all())
    return tasks


def get_task_by_id(session: Session, task_id: int) -> Task | None:
    """
    Возвращает задачу по ее ID.
    Args:
        session: сессия SQLAlchemy.
        task_id: ID задачи.

    Returns:
        Optional[Task]: объект задачи или None.
    """
    return session.get(Task, task_id)


def add_task(session: Session, task_data: dict) -> Task:
    """
    Добавляет новую задачу в проект.
    Args:
        session: сессия SQLAlchemy.
        task_data: словарь с данные задачи.

    Returns:
        Task: объект созданной задачи.

    """

    task = Task(project_id=task_data.get('project_id'),
                parent_id=task_data.get('parent_id'),
                title=task_data.get('title'),
                description=task_data.get('description') or '',
                note=task_data.get('note') or '',
                code_snippet=task_data.get('code_snippet') or '',
                status=task_data.get('status') or 'new',
                is_favorite=task_data.get('is_favorite') or False
                )
    session.add(task)
    session.commit()
    return task


def update_task(session: Session, task_id: int, **kwargs) -> Task | None:
    """
    Обновляет поля задачи при их изменении.
    Args:
        session: сессия SQLAlchemy.
        task_id: ID задачи.
        **kwargs: произвольные именованные аргументы для обновления полей.

    Returns:
        Optional[Task]: объект обновленной задачи или None, если задача не была найдена.
    """

    task = session.get(Task, task_id)
    if not task:
        return None
    for key, value in kwargs.items():
        if hasattr(task, key):
            setattr(task, key, value)
    session.commit()
    return task


def change_task_status(session: Session, task_id: int, new_status: str) -> Task | None:
    """
    Изменяет статус задачи. Если новый статус 'done' или 'archived', устанавливает дату завершения.
    Args:
        session: сессия SQLAlchemy.
        task_id: ID задачи.
        new_status: новый статус задачи (new / in_progress / done / archived)

    Returns:
        Optional[Task]: объект обновленной задачи или None, если задача не была найдена.
    """

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


# -------- Работа с иерархией подзадач --------
def get_task_tree_ids(session: Session, task_id: int) -> list[int]:
    """
    Рекурсивно собирает все ID задач в поддереве, начиная с текущей задачи.
    Args:
        session: сессия SQLAlchemy.
        task_id: ID корневой задачи.

    Returns:
        list[int]: список ID всех задач в поддереве
    """

    def collect_ids(current_id: int):
        ids = [current_id]
        children = session.query(Task).filter(Task.parent_id == task_id).all()
        for child in children:
            ids.extend(collect_ids(child.id))
        return ids
    return collect_ids(task_id)


def archive_subtree(session: Session, task_id: int) -> int:
    """
    Архивирует все дерево задач, начиная с текущей задачи.
    Устанавливает статус archived и дату завершения для каждой задачи.
    Args:
        session: сессия SQLAlchemy.
        task_id: ID корневой задачи.

    Returns:
        int: количество измененных задач
    """

    ids = get_task_tree_ids(session, task_id)
    count = 0
    for tid in ids:
        task = session.get(Task, tid)
        if task and task.status != 'archived':
            task.status = 'archived'
            task.completed_at = datetime.now()
            count += 1
    session.commit()
    return count


def unarchive_subtree(session: Session, task_id: int) -> int:
    """
    Восстанавливает все дерево задач, начиная с текущей задачи.
    Устанавливает статус done и сбрасывает дату завершения для каждой задачи.
    Args:
        session: сессия SQLAlchemy.
        task_id: ID корневой задачи.

    Returns:
        int: количество изменённых задач.
    """

    ids = get_task_tree_ids(session, task_id)
    count = 0
    for tid in ids:
        task = session.get(Task, tid)
        if task and task.status == 'archived':
            task.status = 'done'
            task.completed_at = None
            count += 1
    session.commit()
    return count


def delete_task_with_children(session: Session, task_id: int, delete_children: bool = False) -> bool:
    """
    Удаляет задачу.
    Если был запрос на удаление дочерних задач, то рекурсивно удаляет подзадачи.
    Иначе у дочерних задач обнуляется родитель.
    Args:
        session: сессия SQLAlchemy.
        task_id: ID задачи для удаления.
        delete_children: True, если необходимо удалить подзадачи. По умолчанию False.

    Returns:
        bool: True, если задача(и) была(и) удалена(ы)
    """

    task = session.get(Task, task_id)
    if not task:
        return False

    if delete_children:
        def delete_recursive(del_task):
            for child_task in session.query(Task).filter(Task.parent_id == del_task.id).all():
                delete_recursive(child_task)
            session.delete(del_task)
        delete_recursive(task)
    else:
        for child_task_without_parent in session.query(Task).filter(Task.parent_id == task_id).all():
            child_task_without_parent.parent_id = None
        session.delete(task)
    session.commit()
    return True


def update_parent_status(session: Session, task_id: int) -> None:
    """
    Обновляет статус задачи на основе ее дочерних задач.
    Если все дочерние задачи имею статус done, то задача становится done.
    В противном случае in_progress.
    Затем рекурсивно обновляет статус родительской задачи (если она существует).
    Args:
        session: сессия SQLAlchemy.
        task_id: ID задачи, статус которой нужно обновить.
    """

    task = session.get(Task, task_id)
    if not task:
        return

    # Получаем всех детей (не архивных)
    children = session.query(Task).filter(
        Task.parent_id == task_id,
        Task.status != 'archived'
    ).all()
    if not children:
        return

    all_done = all(t.status == 'done' for t in children)
    new_status = 'done' if all_done else 'in_progress'

    if task.status != new_status:
        task.status = new_status
        session.commit()

    # Рекурсивно обновить родителя (если есть)
    if task.parent_id is not None:
        update_parent_status(session, task.parent_id)
