from pydantic import BaseModel
from datetime import datetime


# ---------- Пользователи ----------
class UserCreate(BaseModel):
    """ Схема для создания пользователя (только имя). """

    name: str


class UserOut(BaseModel):
    """ Схема для ответа с данными пользователя. """

    id: int
    name: str
    created_at: datetime


# ---------- Проекты ----------
class ProjectBase(BaseModel):
    """ Базовые поля проекта (общие для создания и ответа). """

    tech_name: str
    display_name: str
    path: str = ''
    description: str = ''
    technologies: str = '[]'
    is_private: bool = False


class ProjectCreate(ProjectBase):
    """ Схема для создания проекта. Добавляет owner_id. """

    owner_id: int


class ProjectUpdate(BaseModel):
    """ Схема для обновления проекта (все поля опциональны). """

    display_name: str | None = None
    description: str | None = None
    path: str | None = None
    technologies: str | None = None
    is_private: bool | None = None


class ProjectOut(ProjectBase):
    """ Схема для ответа с проектом (добавляет служебные поля). """

    id: int
    owner_id: int | None
    is_favorite: bool
    created_at: datetime
    updated_at: datetime


# ---------- Задачи ----------
class TaskBase(BaseModel):
    """Базовые поля задачи."""

    title: str
    description: str = ''
    note: str = ''
    code_snippet: str = ''
    status: str = 'new'  # new, in_progress, done, archived
    is_private: bool = False
    parent_id: int | None = None


class TaskCreate(TaskBase):
    """ Схема для создания задачи. Добавляет project_id и owner_id. """

    project_id: int
    owner_id: int


class TaskUpdate(BaseModel):
    """ Схема для обновления задачи (все поля опциональны). """

    title: str | None = None
    description: str | None = None
    note: str | None = None
    code_snippet: str | None = None
    status: str | None = None
    is_private: bool | None = None


class TaskOut(TaskBase):
    """ Схема для ответа с задачей. """

    id: int
    project_id: int
    owner_id: int | None
    is_favorite: bool
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
