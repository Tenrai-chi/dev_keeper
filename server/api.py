import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from server import crud
from server.schemas import (
    UserOut, UserCreate, ProjectOut,
    ProjectUpdate, TaskOut, ProjectCreate,
    TaskCreate, TaskUpdate)
from server.database import SessionLocal

router = APIRouter()
logger = logging.getLogger('Server_API')


# ---------- Зависимости ----------
def get_session():
    """
    Получение сессии базы данных через фабрику сессий.
    Используется как зависимость для всех эндпоинтов.

    Yields:
        Session: сессия SQLAlchemy.
    """

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------- Пользователи ----------
@router.post('/users/', response_model=UserOut)
def create_user(user: UserCreate, session: Session = Depends(get_session)) -> UserOut:
    """
     Создаёт нового пользователя с указанным именем.
    Args:
        user: схема с именем пользователя.
        session: сессия базы данных из зависимости.

    Returns:
        UserOut: созданный пользователь с ID и датой создания.
    """

    logger.info(f'Создание пользователя: {user.name}')
    return crud.create_user(session, user)


@router.get('/users/', response_model=list[UserOut])
def get_users(session: Session = Depends(get_session)) -> list[UserOut]:
    """
    Возвращает список всех зарегистрированных пользователей.
    Args:
        session: сессия базы данных из зависимости.

    Returns:
        list[UserOut]: список пользователей, отсортированных по имени.
    """

    logger.debug(f'Запрос списка пользователей')
    return crud.get_users(session)


# ---------- Проекты ----------
@router.get('/projects/', response_model=list[ProjectOut])
def get_all_projects(
    user_id: int = Query(..., description='ID текущего пользователя'),
    session: Session = Depends(get_session)
) -> list[ProjectOut]:
    """
    Возвращает проекты, доступные пользователю:
    - собственные проекты (независимо от приватности);
    - общие проекты других пользователей (is_private=False).

    Args:
        user_id: ID пользователя.
        session: сессия базы данных из зависимости.

    Returns:
        list[ProjectOut]: список проектов, отсортированных по избранному и имени.
    """

    logger.debug(f'Запрос проектов для пользователя {user_id}')
    return crud.get_all_projects(session, user_id)


@router.get('/projects/{project_id}', response_model=ProjectOut)
def get_project_by_id(
    project_id: int,
    user_id: int = Query(..., description='ID текущего пользователя'),
    session: Session = Depends(get_session)
) -> ProjectOut:
    """
    Возвращает проект по ID с проверкой доступа.
    Args:
        project_id: ID проекта.
        user_id: ID пользователя.
        session: сессия базы данных из зависимости.

    Returns:
        ProjectOut: объект проекта.

    Raises:
        HTTPException: 404, если проект не найден или доступ запрещён.
    """

    logger.debug(f'Запрос проекта {project_id} для пользователя {user_id}')
    project = crud.get_project_by_id(session, project_id, user_id)
    if not project:
        logger.warning(f'Проект {project_id} не найден или недоступен для пользователя {user_id}')
        raise HTTPException(status_code=404, detail='Проект не найден или недоступен~')
    return project


@router.post('/projects/', response_model=ProjectOut)
def add_project(
    project: ProjectCreate,
    session: Session = Depends(get_session)
) -> ProjectOut:
    """
    Создаёт новый проект.
    Args:
        project: схема с данными проекта.
        session: сессия базы данных из зависимости.

    Returns:
        ProjectOut: созданный проект с ID и датами.
    """

    logger.info(f'Создание проекта: {project.display_name}. Владелец {project.owner_id}')
    return crud.add_project(session, project)


@router.put('/projects/{project_id}', response_model=ProjectOut)
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    user_id: int = Query(..., description='ID текущего пользователя'),
    session: Session = Depends(get_session)
) -> ProjectOut:
    """
    Обновляет проект. Публичный может редактировать любой пользователь,
    приватный – только владелец.
    Args:
        project_id: ID проекта.
        project_update: схема с обновляемыми полями.
        user_id: ID пользователя.
        session: сессия базы данных из зависимости.

    Returns:
        ProjectOut: обновлённый проект.

    Raises:
        HTTPException: 403, если недостаточно прав.
    """

    logger.info(f'Обновление проекта {project_id} пользователем {user_id}')
    project = crud.update_project(session, project_id, project_update, user_id)
    if not project:
        logger.warning(f'Пользователь {user_id} не может обновить проект {project_id}')
        raise HTTPException(status_code=403, detail='Сорьки, не твой проект~')
    return project


@router.delete('/projects/{project_id}', response_model=dict)
def delete_project(
    project_id: int,
    user_id: int = Query(..., description='ID текущего пользователя'),
    session: Session = Depends(get_session)
) -> dict:
    """
    Запрос на удаление проекта.
    Args:
        project_id: ID проекта.
        user_id: ID пользователя.
        session: сессия базы данных из зависимости.

    Returns:
        dict: {'success': True} при успехе.

    Raises:
        HTTPException: 403, если недостаточно прав.
    """

    logger.info(f'Удаление проекта {project_id} пользователем {user_id}')
    if not crud.delete_project(session, project_id, user_id):
        logger.warning(f'Пользователь {user_id} не может удалить проект {project_id}')
        raise HTTPException(status_code=403, detail='Сорьки, не твой проект~')
    return {'success': True}


@router.post('/projects/{project_id}/favorite', response_model=ProjectOut)
def toggle_project_favorite(
    project_id: int,
    session: Session = Depends(get_session)
) -> ProjectOut:
    """
    Переключает глобальный статус «избранное» для проекта (доступно всем).
    Args:
        project_id: ID проекта.
        session: сессия базы данных из зависимости.

    Returns:
        ProjectOut: обновлённый проект с новым значением is_favorite.

    Raises:
        HTTPException: 404, если проект не найден.
    """

    logger.info(f'Переключение избранного для проекта {project_id}')
    project = crud.toggle_project_favorite(session, project_id)
    if not project:
        logger.warning(f'Проект {project_id} не найден')
        raise HTTPException(status_code=404, detail='Проект не найден')
    return project


@router.post('/projects/{project_id}/toggle-private', response_model=ProjectOut)
def toggle_project_private(
    project_id: int,
    user_id: int = Query(..., description='ID текущего пользователя'),
    session: Session = Depends(get_session)
) -> ProjectOut:
    """
    Переключает флаг приватности проекта (только для владельца).
    Args:
        project_id: ID проекта.
        user_id: ID пользователя.
        session: сессия базы данных из зависимости.

    Returns:
         ProjectOut: обновлённый проект с новым значением is_private.

     Raises:
        HTTPException: 403, если пользователь не владелец.
    """

    logger.info(f'Переключение приватности проекта {project_id} пользователем {user_id}')
    project = crud.toggle_private_project(session, project_id, user_id)
    if not project:
        logger.warning(f'Пользователь {user_id} не может изменить приватность проекта {project_id}')
        raise HTTPException(status_code=403, detail='Ты не можешь поменять приватность~')
    return project


@router.get('/projects/search/', response_model=list[ProjectOut])
def search_projects(
    q: str,
    user_id: int = Query(..., description='ID текущего пользователя'),
    session: Session = Depends(get_session)
) -> list[ProjectOut]:
    """
    Поиск проектов по названию или технологиям (без учёта регистра).
    Учитываются только проекты, доступные пользователю.
    Args:
        q: текст для поиска.
        user_id: ID пользователя.
        session: сессия базы данных из зависимости.

    Returns:
        List[ProjectOut]: список проектов, соответствующих запросу.
    """

    logger.debug(f'Поиск проектов по запросу "{q}" для пользователя {user_id}')
    return crud.search_projects(session, q, user_id)


# ---------- Задачи ----------
@router.get('/tasks/', response_model=list[TaskOut])
def get_tasks(
    project_id: int = Query(..., description='ID проекта'),
    user_id: int = Query(..., description='ID текущего пользователя'),
    include_archived: bool = False,
    session: Session = Depends(get_session)
) -> list[TaskOut]:
    """
     Возвращает задачи проекта, доступные пользователю.
    Args:
        project_id: ID проекта.
        user_id: ID пользователя.
        include_archived: включать ли архивные задачи.
        session: сессия базы данных из зависимости.

    Returns:
        List[TaskOut]: список задач, отсортированных по статусу и избранному.
    """

    logger.debug(f'Запрос задач проекта {project_id} для пользователя {user_id}, include_archived={include_archived}')
    return crud.get_tasks_by_project(session, project_id, user_id, include_archived)


@router.get('/tasks/{task_id}', response_model=TaskOut)
def get_task_by_id(
    task_id: int,
    user_id: int = Query(..., description='ID текущего пользователя'),
    session: Session = Depends(get_session)
) -> TaskOut:
    """
    Возвращает задачу по ID с проверкой доступа.
    Args:
        task_id: ID задачи.
        user_id: ID пользователя.
        session: сессия базы данных из зависимости.

    Returns:
         TaskOut: объект задачи.

    Raises:
        HTTPException: 404, если задача не найдена или доступ запрещён.
    """

    logger.debug(f'Запрос задачи {task_id} для пользователя {user_id}')
    task = crud.get_task_by_id(session, task_id, user_id)
    if not task:
        logger.warning(f'Задача {task_id} не найдена или недоступна для пользователя {user_id}')
        raise HTTPException(status_code=404, detail='Задача не найдена~')
    return task


@router.post('/tasks/', response_model=TaskOut)
def add_task(
    task: TaskCreate,
    session: Session = Depends(get_session)
) -> TaskOut:
    """
    Создаёт новую задачу в проекте.
    Args:
        task: схема с данными задачи.
        session: сессия базы данных из зависимости.

    Returns:
        TaskOut: созданная задача с ID и датами.
    """

    logger.info(f'Создание задачи в проекте {task.project_id}. Владелец {task.owner_id}')
    return crud.add_task(session, task)


@router.put('/tasks/{task_id}', response_model=TaskOut)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    user_id: int = Query(..., description='ID текущего пользователя'),
    session: Session = Depends(get_session)
) -> TaskOut:
    """
    Обновляет задачу. Публичную может редактировать любой пользователь,
    приватную – только владелец.
    Args:
        task_id: ID задачи.
        task_update: схема с обновляемыми полями.
        user_id: ID пользователя.
        session: сессия базы данных из зависимости.

    Returns:
        TaskOut: обновлённая задача.

    Raises:
        HTTPException: 403, если недостаточно прав.
    """

    logger.info(f'Обновление задачи {task_id} пользователем {user_id}')
    task = crud.update_task(session, task_id, task_update, user_id)
    if not task:
        logger.warning(f'Пользователь {user_id} не может обновить задачу {task_id}')
        raise HTTPException(status_code=403, detail='Сорьки, ты не можешь изменить задачу~')
    return task


@router.delete('/tasks/{task_id}', response_model=dict)
def delete_task(
    task_id: int,
    user_id: int = Query(..., description='ID текущего пользователя'),
    delete_children: bool = False,
    session: Session = Depends(get_session)
) -> dict:
    """
    Удаляет задачу. Публичную может удалить любой пользователь,
    приватную – только владелец.
    Если delete_children=True, удаляет всё поддерево.
    Args:
        task_id: ID задачи.
        user_id: ID пользователя.
        delete_children: удалить ли подзадачи.
        session: сессия базы данных из зависимости.

    Returns:
        dict: {'success': True} при успехе.

    Raises:
        HTTPException: 403, если недостаточно прав.
    """

    logger.info(f'Удаление задачи {task_id} пользователем {user_id}, delete_children={delete_children}')
    if not crud.delete_task(session, task_id, user_id, delete_children):
        logger.warning(f'Не удалось удалить задачу {task_id} пользователем '
                       f'{user_id}, delete_children={delete_children}')
        raise HTTPException(status_code=403, detail='Сорьки, ты не можешь удалить задачу~')
    return {'success': True}


@router.post('/tasks/{task_id}/favorite', response_model=TaskOut)
def toggle_task_favorite(
    task_id: int,
    session: Session = Depends(get_session)
) -> TaskOut:
    """
    Переключает глобальный статус «избранное» для задачи (доступно всем).
    Args:
        task_id: ID задачи.
        session: сессия базы данных из зависимости.

    Returns:
        TaskOut: обновлённая задача с новым значением is_favorite.

    Raises:
        HTTPException: 404, если задача не найдена.
    """

    logger.info(f'Переключение избранного для задачи {task_id}')
    task = crud.toggle_task_favorite(session, task_id)
    if not task:
        logger.warning(f'Задача {task_id} не найдена')
        raise HTTPException(status_code=404, detail='Задача не найдена~')
    return task


@router.post('/tasks/{task_id}/toggle-private', response_model=TaskOut)
def toggle_task_private(
    task_id: int,
    user_id: int = Query(..., description='ID текущего пользователя'),
    session: Session = Depends(get_session)
) -> TaskOut:
    """
    Переключает флаг приватности задачи (только для владельца).
    Args:
        task_id: ID задачи.
        user_id: ID пользователя.
        session: сессия базы данных из зависимости.

    Returns:
        TaskOut: обновлённая задача с новым значением is_private.

    Raises:
        HTTPException: 403, если пользователь не владелец.
    """

    logger.info(f'Переключение приватности задачи {task_id} пользователем {user_id}')
    task = crud.toggle_private_task(session, task_id, user_id)
    if not task:
        logger.warning(f'Пользователь {user_id} не может изменить приватность задачи {task_id}')
        raise HTTPException(status_code=403, detail='Сорьки, ты не можешь изменить приватность проекта~')
    return task


@router.post('/tasks/{task_id}/archive', response_model=dict)
def archive_task_subtree(
    task_id: int,
    user_id: int = Query(..., description='ID текущего пользователя'),
    session: Session = Depends(get_session)
) -> dict:
    """
    Архивирует задачу и все её подзадачи (рекурсивно).
    Публичные задачи могут архивировать все, приватные – только владелец.
    Args:
        task_id: ID корневой задачи.
        user_id: ID пользователя.
        session: сессия базы данных из зависимости.

    Returns:
        dict: {'archived_count': количество изменённых задач}.

    Raises:
        HTTPException: 403, если недостаточно прав.
    """

    logger.info(f'Архивация поддерева задачи {task_id} пользователем {user_id}')
    count = crud.archive_subtree(session, task_id, user_id)
    if count == 0:
        logger.warning(f'Не удалось архивировать поддерево задачи {task_id} пользователем {user_id}')
        raise HTTPException(status_code=403, detail='Сорьки, ты не можешь архивировать эту задачу~')
    return {'archived_count': count}


@router.post('/tasks/{task_id}/unarchive', response_model=dict)
def unarchive_task_subtree(
    task_id: int,
    user_id: int = Query(..., description='ID текущего пользователя'),
    session: Session = Depends(get_session)
) -> dict:
    """
    Восстанавливает задачу и все её подзадачи (устанавливает статус 'done').
    Публичные задачи могут восстанавливать все, приватные – только владелец.
    Args:
        task_id: ID корневой задачи.
        user_id: ID пользователя.
        session: сессия базы данных из зависимости.

    Returns:
        dict: {'unarchived_count': количество восстановленных задач}.

    Raises:
        HTTPException: 403, если недостаточно прав.
    """

    logger.info(f'Восстановление поддерева задачи {task_id} пользователем {user_id}')
    count = crud.unarchive_subtree(session, task_id, user_id)
    if count == 0:
        logger.warning(f'Не удалось восстановить поддерево задачи {task_id} пользователем {user_id}')
        raise HTTPException(status_code=403, detail='Сорьки, ты не можешь разархивировать эту задачу~')
    return {'unarchived_count': count}


@router.post('/tasks/{task_id}/status', response_model=TaskOut)
def change_task_status(
    task_id: int,
    new_status: str = Query(..., description='Новый статус: new, in_progress, done, archived'),
    user_id: int = Query(..., description='ID текущего пользователя'),
    session: Session = Depends(get_session)
) -> TaskOut:
    """
    Изменяет статус задачи. Публичную могут менять все,
    приватную – только владелец.
    Args:
        task_id: ID задачи.
        new_status: новый статус (new, in_progress, done, archived).
        user_id: ID пользователя.
        session: сессия базы данных из зависимости.

    Returns:
        TaskOut: обновлённая задача.

    Raises:
        HTTPException: 403, если недостаточно прав.
    """

    logger.info(f'Изменение статуса задачи {task_id} на "{new_status}" пользователем {user_id}')
    task = crud.change_task_status(session, task_id, new_status, user_id)
    if not task:
        logger.warning(f'Не удалось изменить статус задачи {task_id} пользователем {user_id}')
        raise HTTPException(status_code=403, detail='Сорьки, ты не можешь изменить статус~')
    return task
