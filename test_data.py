import json
from sqlalchemy.orm import Session
from database import Project, Task


def add_test_data(session: Session) -> None:
    """
    Добавляет тестовые проекты и задачи, только если таблицы пусты.
    """
    # Если уже есть проекты, не добавляем заново
    if session.query(Project).count() > 0:
        print("В БД уже есть проекты, тестовые данные не добавлены.")
        return

    # Проект 1
    p1 = Project(
        tech_name="online_store",
        display_name="Магазин на DRF (учебный)",
        path="/home/user/projects/online_store",
        description="Интернет-магазин на Django Rest Framework + React",
        technologies=json.dumps(["django", "drf", "react", "postgresql"])
    )
    session.add(p1)
    session.flush()  # получаем id

    tasks_p1 = [
        Task(project_id=p1.id, title="Настроить модель пользователя", description="Кастомная модель User", priority_order=0),
        Task(project_id=p1.id, title="Создать API для товаров", priority_order=1),
        Task(project_id=p1.id, title="Написать тесты для корзины", priority_order=2),
        Task(project_id=p1.id, title="Подключить Celery для фоновых задач", priority_order=3),
    ]
    session.add_all(tasks_p1)

    # Проект 2
    p2 = Project(
        tech_name="telegram_bot",
        display_name="Телеграм-бот для заметок",
        path="/home/user/projects/tgbot",
        description="Бот на aiogram для ведения заметок",
        technologies=json.dumps(["aiogram", "redis", "sqlalchemy"])
    )
    session.add(p2)
    session.flush()

    tasks_p2 = [
        Task(project_id=p2.id, title="Спроектировать схему БД", priority_order=0),
        Task(project_id=p2.id, title="Написать обработчик команды /start", priority_order=1),
        Task(project_id=p2.id, title="Реализовать напоминания", priority_order=2),
        Task(project_id=p2.id, title="Добавить логирование", priority_order=3),
    ]
    session.add_all(tasks_p2)

    # Проект 3
    p3 = Project(
        tech_name="devkeeper",
        display_name="DevKeeper (это приложение)",
        path="/home/user/projects/devkeeper",
        description="Десктопное приложение для управления проектами",
        technologies=json.dumps(["pyside6", "sqlalchemy", "sqlite"])
    )
    session.add(p3)
    session.flush()

    tasks_p3 = [
        Task(project_id=p3.id, title="Спроектировать UI", priority_order=0),
        Task(project_id=p3.id, title="Реализовать дерево проектов", priority_order=1),
        Task(project_id=p3.id, title="Добавить заметки к задачам", priority_order=2),
        Task(project_id=p3.id, title="Написать парсинг requirements", priority_order=3),
    ]
    session.add_all(tasks_p3)

    session.commit()
    print("Тестовые данные добавлены (3 проекта, 12 задач).")