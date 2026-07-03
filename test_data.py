import json
import logging

from sqlalchemy.orm import Session

from database import Project, Task

logger = logging.getLogger(__name__)


def add_test_data(session: Session) -> None:
    """ Добавление тестовых данных при запросе """

    # Проект 1
    p1 = Project(
        tech_name='online_store',
        display_name='Магазин на DRF (учебный)',
        path='/projects/online_store',
        description='Интернет-магазин на Django Rest Framework + React',
        technologies=json.dumps(['django', 'drf', 'react', 'postgresql'])
    )
    session.add(p1)
    session.flush()

    tasks_p1 = [
        Task(project_id=p1.id, title='Настроить модель пользователя', description='Кастомная модель User', priority_order=0),
        Task(project_id=p1.id, title='Создать API для товаров', priority_order=1),
        Task(project_id=p1.id, title='Написать тесты для корзины', priority_order=2),
        Task(project_id=p1.id, title='Подключить Celery для фоновых задач', priority_order=3),
    ]
    session.add_all(tasks_p1)

    # Проект 2
    p2 = Project(
        tech_name='telegram_bot',
        display_name='Телеграм-бот для заметок',
        path='/projects/tgbot',
        description='Бот на aiogram для ведения заметок',
        technologies=json.dumps(['aiogram', 'redis', 'sqlalchemy'])
    )
    session.add(p2)
    session.flush()

    tasks_p2 = [
        Task(project_id=p2.id, title='Спроектировать схему БД', priority_order=0),
        Task(project_id=p2.id, title='Написать обработчик команды /start', priority_order=1),
        Task(project_id=p2.id, title='Реализовать напоминания', priority_order=2),
        Task(project_id=p2.id, title='Добавить логирование', priority_order=3),
    ]
    session.add_all(tasks_p2)

    # Проект 3
    p3 = Project(
        tech_name='dev_keeper',
        display_name='DevKeeper',
        path='/projects/dev_keeper',
        description='Десктопное приложение для управления проектами',
        technologies=json.dumps(['pyside6', 'sqlalchemy', 'sqlite'])
    )
    session.add(p3)
    session.flush()

    tasks_p3 = [
        Task(project_id=p3.id, title='Спроектировать UI', priority_order=0),
        Task(project_id=p3.id, title='Реализовать дерево проектов', priority_order=1),
        Task(project_id=p3.id, title='Добавить заметки к задачам', priority_order=2),
        Task(project_id=p3.id, title='Написать парсинг requirements', priority_order=3),
    ]
    session.add_all(tasks_p3)

    session.commit()
    logging.info('Тестовые данные добавлены (3 проекта, 12 задач).')