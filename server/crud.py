import logging
from sqlalchemy import select, case
from sqlalchemy.orm import Session
from datetime import datetime

from server.database import Users, Task, Project
from server.schemas import UserCreate, ProjectCreate, ProjectUpdate, TaskCreate, TaskUpdate

logger = logging.getLogger(__name__)


# ---------- Пользователи ----------
def get_users(session: Session) -> list[Users]:
    """
    Возвращает список всех пользователей.
    Args:
        session: сессия SQLite.
    Returns:
        users: список всех пользователей.
    """

    smtm_users = (
        select(Users)
        .order_by(Users.name)
    )
    users = list(session.execute(smtm_users).scalars().all())

    return users


def create_user(session: Session, user: UserCreate) -> Users:
    """
    Создает пользователя и возвращает его.
    Args:
        session: сессия SQLite.
        user: схема пользователя для создания.

    Returns:
        new_user: объект созданного пользователя
    """

    new_user = Users(name=user.name)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user


# ---------- Проекты ----------
def get_all_projects(session: Session, user_id: int) -> list[Project]:
    """
    Возвращает проекты, доступные пользователю: свои и общие.
    Args:
        session: сессия SQLite.
        user_id: ID пользователя.

    Returns:
        projects: список проектов, доступных пользователю.
    """

    stmt_projects = (
        select(Project)
        .where((Project.owner_id == user_id) | (Project.is_private == False))
        .order_by(
            Project.is_favorite.desc(),
            Project.display_name
        )
    )

    projects = list(session.execute(stmt_projects).scalars().all())
    logger.info(f'Запрошено {len(projects)} проектов')
    return projects


def get_project_by_id(session: Session, project_id: int, user_id: int
                      ) -> Project | None:
    """
    Возвращает проект по его ID.
    Если пользователь не имеет доступа, то возвращает None

    Args:
        session: сессия SQLite.
        project_id: ID проекта.
        user_id: ID пользователя.

    Returns:
        project: объект проекта.
    """

    stmt_project = (
        select(Project)
        .where(Project.id == project_id,
               (Project.owner_id == user_id) | (Project.is_private == False)
               )
    )
    project = session.execute(stmt_project).scalar_one_or_none()
    if project:
        logger.info(f'Получен проект ID: {project.id}')
    else:
        logger.warning(f'Не удалось получить проект ID: {project_id}')
    return project


def add_project(session: Session, project: ProjectCreate) -> Project:
    """
    Создает проект.
    Args:
        session: сессия SQLite.
        project: схема проекта для создания.

    Returns:
        new_project: объект созданного проекта
    """

    new_project = Project(
        tech_name=project.tech_name,
        display_name=project.display_name,
        path=project.path,
        description=project.description,
        technologies=project.technologies,
        owner_id=project.owner_id,
        is_private=project.is_private,
    )
    session.add(new_project)
    session.commit()
    session.refresh(new_project)
    logger.info(f'Создан проект ID: {new_project.id}')
    return new_project


def update_project(session: Session, project_id: int, project_update: ProjectUpdate, user_id: int
                   ) -> Project | None:
    """
    Обновляет поля проекта при изменении.
    Args:
        session: сессия SQLite.
        project_id: ID проекта.
        project_update: схема проекта для обновления данных.
        user_id: ID пользователя.

    Returns:
        project: объект обновленного проекта.
    """

    project = session.get(Project, project_id)
    if not project:
        logger.info(f'Проект ID: {project_id} не найден')
        return None

    if project.is_private and project.owner_id != user_id:
        logger.info(f'Попытка пользователя ID {user_id} изменить проект ID {project_id} '
                    f'пользователя ID {project.owner_id}')
        return None

    update_data = project_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    project.updated_at = datetime.now()
    session.commit()
    session.refresh(project)
    logger.info(f'Обновлен проект ID: {project.id}')
    return project


def delete_project(session: Session, project_id: int, user_id: int) -> bool:
    """
    Удаляет проект.
    Args:
        session: сессия SQLite.
        project_id: ID проекта для удаления.
        user_id: ID пользователя.

    Returns:
        bool: True, если удаление прошло успешно, иначе False.
    """

    project = session.get(Project, project_id)
    if not project:
        return False
    if project.is_private and project.owner_id != user_id:
        return False
    session.delete(project)
    session.commit()
    return True


def toggle_project_favorite(session: Session, project_id: int) -> Project | None:
    """
    Переключает статус избранного у проекта.
    Проверяет, что пользователь является владельцем проекта.

    Args:
        session: сессия SQLAlchemy.
        project_id: ID проекта.

    Returns:
        project: обновлённый проект или None, если проект не найден
    """

    project = session.get(Project, project_id)
    if not project:
        return None
    project.is_favorite = not project.is_favorite
    session.commit()
    session.refresh(project)
    return project


def search_projects(session: Session, search_text: str, user_id: int) -> list[Project]:
    """
    Возвращает проекты, в которых выполнен поиск по названию и используемым технологиям.
    Доступны только общие и личные проекты, где пользователь автор.
    Args:
        session: сессия SQLAlchemy.
        search_text: текст для поиска.
        user_id: ID пользователя.

    Returns:
        result_projects: список проектов, удовлетворяющих поиску.
    """

    if not search_text or not search_text.strip():
        return get_all_projects(session, user_id)

    search_lower = search_text.lower()
    all_projects = get_all_projects(session, user_id)
    result_projects = []
    for project in all_projects:
        if (search_lower in project.display_name.lower() or
                search_lower in project.technologies.lower()):
            result_projects.append(project)
    return result_projects


def toggle_private_project(session: Session, project_id: int, user_id: int) -> Project | None:
    """
    Переключает флаг is_private у проекта (доступно только владельцу).
    Args:
        session: session: сессия SQLite.
        project_id: ID проекта.
        user_id: ID пользователя.

    Returns:
        Project | None: объект измененного проекта.
    """

    project = session.get(Project, project_id)
    if not project or project.owner_id != user_id:
        return None
    project.is_private = not project.is_private
    session.commit()
    session.refresh(project)
    return project


# ---------- Задачи ----------
def get_tasks_by_project(session: Session, project_id: int,
                         user_id: int, include_archived: bool = False
                         ) -> list[Task]:
    """
    Возвращает задачи проекта, доступные пользователю.
    Args:
        session: сессия SQLite.
        project_id: ID проекта.
        user_id: ID пользователя.
        include_archived: True, если нужно добавлять и архивные записи.

    Returns:
        tasks: список задач проекта.
    """

    stmt_tasks = (
        select(Task)
        .where(Task.project_id == project_id,
               (Task.owner_id == user_id) | (Task.is_private == False)
               )
    )
    if not include_archived:
        stmt_tasks = stmt_tasks.where(Task.status != 'archived')

    status_order = {
        'in_progress': 0,
        'new': 1,
        'done': 2,
        'archived': 3
    }
    stmt_tasks = stmt_tasks.order_by(
        case(status_order, value=Task.status),
        Task.is_favorite.desc()
    )
    tasks = list(session.execute(stmt_tasks).scalars().all())
    return tasks


def get_task_by_id(session: Session, task_id: int, user_id: int) -> Task | None:
    """
    Возвращает задачу по ее ID.
    Args:
        session: сессия SQLite.
        task_id: ID задачи.
        user_id: ID пользователя.

    Returns:
        task: объект задачи или None.
    """

    stmt_task = (
        select(Task)
        .where(
            Task.id == task_id,
            (Task.owner_id == user_id) | (Task.is_private == False)
        )
    )
    task = session.execute(stmt_task).scalar_one_or_none()
    return task


def add_task(session: Session, task: TaskCreate) -> Task:
    """
    Создает задачу и возвращает ее.
    Args:
        session: сессия SQLite.
        task: схема задачи для создания.

    Returns:
        new_task: объект созданной задачи.
    """

    new_task = Task(
        project_id=task.project_id,
        parent_id=task.parent_id,
        title=task.title,
        description=task.description,
        note=task.note,
        code_snippet=task.code_snippet,
        status=task.status,
        owner_id=task.owner_id,
        is_private=task.is_private,
    )
    session.add(new_task)
    session.commit()
    session.refresh(new_task)
    if new_task.parent_id is not None:
        update_parent_status(session, new_task.parent_id)
    return new_task


def update_task(session: Session, task_id: int, task_update: TaskUpdate, user_id: int
                ) -> Task | None:
    """
    Обновляет данные задачи. А затем возвращает измененный объект при успехе.
    Args:
        session: сессия SQLite.
        task_id: ID задачи для изменения.
        task_update: схема данных задачи для изменения.
        user_id: ID пользователя.

    Returns:
        Task | None: объект измененной задачи или None, при неудаче.
    """

    task = session.get(Task, task_id)
    if not task:
        return None
    if task.is_private and task.owner_id != user_id:
        return None
    update_data = task_update.model_dump(exclude_unset=True)

    new_status = update_data.get('status')
    if new_status in ('done', 'archived'):
        task.completed_at = datetime.now()
    elif new_status is not None:
        task.completed_at = None
    for key, value in update_data.items():
        setattr(task, key, value)
    task.updated_at = datetime.now()
    session.commit()
    session.refresh(task)
    return task


def delete_task(session: Session, task_id: int, user_id: int, delete_children: bool = False) -> bool:
    """
    Удаление задачи.
    Args:
        session: сессия SQLite.
        task_id: ID задачи для удаления.
        user_id: ID пользователя.
        delete_children: True, если необходимо удалить дочерние задачи.

    Returns:
        bool: True, если удаление прошло успешно, иначе False.
    """

    task = session.get(Task, task_id)
    if not task:
        return False
    if task.is_private and task.owner_id != user_id:
        return False
    if delete_children:
        # Рекурсивно удаляем все подзадачи
        def delete_recursive(t):
            for child in session.query(Task).filter(Task.parent_id == t.id).all():
                delete_recursive(child)
            session.delete(t)
        delete_recursive(task)
    else:
        # Обнуляем parent_id у детей
        for child in session.query(Task).filter(Task.parent_id == task_id).all():
            child.parent_id = None
        session.delete(task)
    session.commit()
    return True


def toggle_task_favorite(session: Session, task_id: int) -> Task | None:
    """
    Изменяет статус избранного у задачи.
    Args:
        session: сессия SQLite.
        task_id: ID задачи.
    Returns:
        Task | None: объект измененной задачи или None.
    """

    task = session.get(Task, task_id)
    if not task:
        return None
    task.is_favorite = not task.is_favorite
    session.commit()
    session.refresh(task)
    return task


def change_task_status(session: Session, task_id: int, new_status: str, user_id: int
                       ) -> Task | None:
    """
    Изменяет статус задачи. Если новый статус 'done' или 'archived', устанавливает дату завершения.
    Args:
        session: сессия SQLite.
        task_id: ID задачи.
        new_status: новый статус задачи.
        user_id: ID пользователя.

    Returns:
        task: объект измененной задачи.
    """

    task = session.get(Task, task_id)
    if not task:
        return None
    if task.is_private and task.owner_id != user_id:
        return None
    task.status = new_status
    if new_status in ('done', 'archived'):
        task.completed_at = datetime.now()
    else:
        task.completed_at = None
    session.commit()
    session.refresh(task)
    if task.parent_id is not None:
        update_parent_status(session, task.parent_id)
    return task


def toggle_private_task(session: Session, task_id: int, user_id: int) -> Task | None:
    """
    Переключает флаг is_private у задачи (доступно только владельцу).
    Args:
        session: сессия SQLite.
        task_id: ID задачи.
        user_id: ID пользователя.

    Returns:
        Task | None: объект измененной задачи или None.
    """

    print(f'Пришел запрос от пользователя ID {user_id}')
    task = session.get(Task, task_id)
    print(f'Хозяин задачи ID {task.owner_id}')
    if not task or task.owner_id != user_id:
        print(f'Запрос от пользователя не имеющего доступ к  {task.id}')
        return None
    task.is_private = not task.is_private
    session.commit()
    session.refresh(task)
    return task


# -------- Работа с иерархией подзадач --------
def get_task_tree_ids(session: Session, task_id: int) -> list[int]:
    """
    Рекурсивно собирает все ID задач в поддереве, начиная с текущей задачи.
    Args:
        session: сессия SQLite.
        task_id: ID задачи.

    Returns:
        list[int]: список ID всех задач в поддереве
    """

    def collect_ids(current_id: int):
        ids = [current_id]
        children = session.query(Task).filter(Task.parent_id == current_id).all()
        for child in children:
            ids.extend(collect_ids(child.id))
        return ids
    return collect_ids(task_id)


def archive_subtree(session: Session, task_id: int, user_id: int) -> int:
    """
    Архивирует все дерево задач, начиная с текущей задачи.
    Устанавливает статус archived и дату завершения для каждой задачи.
    Args:
        session: сессия SQLAlchemy.
        task_id: ID корневой задачи.
        user_id: ID пользователя.

    Returns:
        int: количество измененных задач
    """

    ids = get_task_tree_ids(session, task_id)
    for tid in ids:
        task = session.get(Task, tid)
        if not task:
            return 0
        if task.is_private and task.owner_id != user_id:
            return 0
    count = 0
    for tid in ids:
        task = session.get(Task, tid)
        if task and task.status != 'archived':
            task.status = 'archived'
            task.completed_at = datetime.now()
            count += 1
    session.commit()
    return count


def unarchive_subtree(session: Session, task_id: int, user_id: int) -> int:
    """
    Восстанавливает всё дерево задач, начиная с текущей задачи.
    Args:
        session: сессия SQLAlchemy.
        task_id: ID корневой задачи.
        user_id: ID пользователя.

    Returns:

    """

    ids = get_task_tree_ids(session, task_id)
    for tid in ids:
        task = session.get(Task, tid)
        if not task:
            return 0
        if task.is_private and task.owner_id != user_id:
            return 0
    count = 0
    for tid in ids:
        task = session.get(Task, tid)
        if task and task.status == 'archived':
            task.status = 'done'
            task.completed_at = None
            count += 1
    session.commit()
    return count


def delete_task_with_children(session: Session, task_id: int, user_id: int, delete_children: bool = False) -> bool:
    """
    Удаляет задачу. Если delete_children=True, удаляет все подзадачи (с проверкой прав).
    Иначе только задачу, а подзадачи становятся корневыми.
    Args:
        session: сессия SQLAlchemy.
        task_id: ID корневой задачи.
        user_id: ID пользователя.
        delete_children: True, если нужно удалить задачу с подзадачами.

    Returns:
        bool: True, если задача(и) была(и) удалена(ы)
    """

    task = session.get(Task, task_id)
    if not task or task.owner_id != user_id:
        return False
    if delete_children:
        # Собираем все ID поддерева (включая текущую)
        ids = get_task_tree_ids(session, task_id)
        # Проверяем права на все задачи
        for tid in ids:
            t = session.get(Task, tid)
            if not t or t.owner_id != user_id:
                return False

        def delete_recursive(t):
            for child in session.query(Task).filter(Task.parent_id == t.id).all():
                delete_recursive(child)
            session.delete(t)
        delete_recursive(task)
    else:
        # Обнуляем parent_id у детей
        for child in session.query(Task).filter(Task.parent_id == task_id).all():
            child.parent_id = None
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
    if not task or task.parent_id is None:
        return
    parent = session.get(Task, task.parent_id)
    if not parent:
        return
    children = session.query(Task).filter(
        Task.parent_id == parent.id,
        Task.status != 'archived'
    ).all()
    if not children:
        return
    all_done = all(t.status == 'done' for t in children)
    new_status = 'done' if all_done else 'in_progress'
    if parent.status != new_status:
        parent.status = new_status
        session.commit()
    update_parent_status(session, parent.id)
