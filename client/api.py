import requests
import logging

logger = logging.getLogger('Client_API')


class APIClient:
    """ Клиент для взаимодействия с сервером DevKeeper по HTTP. """

    def __init__(self, base_url: str):
        """
        Инициализация API клиента.
        Args:
            base_url (str): базовый URL сервера
        """

        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        logger.info(f'API клиент инициализирован с URL: {self.base_url}')

    def update_base_url(self, new_url: str) -> None:
        """ Обновляет базовый URL (например, при смене настроек). """

        self.base_url = new_url.rstrip('/')
        logger.info(f'Обновлён базовый URL клиента: {self.base_url}')

    def _request(self, method: str, endpoint: str, params: dict | None = None,
                 data: dict | None = None) -> dict | list[dict]:
        """
        Выполняет HTTP-запрос и возвращает JSON-ответ.
        При ошибке поднимает исключение с деталями.
        Args:
            method: метод запроса GET, POST, PUT, DELETE.
            endpoint: эндпоинт (относительный путь, например '/users/').
            params: параметры запроса (для GET).
            data: данные для отправки в теле запроса (для POST, PUT).

        Returns:
            dict | list[dict]: декодированный JSON-ответ сервера (словарь или список).
        """

        url = f'{self.base_url}/{endpoint.lstrip("/")}'
        logger.debug(f'Отправка {method} запроса к {url}, params={params}, data={data}')
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=10
            )
            response.raise_for_status()
            result = response.json() if response.text else {}
            logger.debug(f'Успешный ответ от {url}: {result}')
            return result

        except requests.exceptions.RequestException as error:
            logger.error(f'Ошибка запроса к {url}: {error}')
            # Отправляем ошибку в gui, чтобы стриггерить окна и предупреждения, если необходимо.
            if error.response is not None and error.response.text:
                try:
                    detail = error.response.json().get('detail', str(error))
                except:
                    detail = error.response.text
            else:
                detail = str(error)
                # Поднимаем исключение с понятным сообщением
            raise Exception(f'Ошибка API: {detail}') from error

    def test_connection(self) -> bool:
        """
        todo использовать при изменения настроек подключения
        Проверяет доступность сервера (запрос к корневому эндпоинту).
        Returns:
            bool: True, если получен ответ, False, если произошла ошибка.
        """

        try:
            response = self.session.get(f'{self.base_url}/users/', timeout=5)
            return response.status_code == 200
        except:
            return False

    # ---------- Пользователи ----------
    def get_users(self) -> list[dict]:
        """ Возвращает список всех пользователей. """

        logger.debug('Запрос списка пользователей')
        return self._request('GET', '/users/')

    def create_user(self, name: str) -> dict:
        """
        Создаёт нового пользователя.
        Args:
            name: Имя для создания пользователя.

        Returns:
            dict: данные созданного пользователя.
        """

        logger.info(f'Создание пользователя с именем "{name}"')
        return self._request('POST', '/users/', data={'name': name})

    # ---------- Проекты ----------
    def get_all_projects(self, user_id: int) -> list[dict]:
        """
        Возвращает проекты, доступные пользователю.
        Args:
            user_id: ID текущего пользователя.

        Returns:
            list[dict]: список проектов, отсортированных по избранному и имени.
        """

        logger.debug(f'Запрос проектов для пользователя {user_id}')
        return self._request('GET', '/projects/', params={'user_id': user_id})

    def get_project_by_id(self, project_id: int, user_id: int) -> dict:
        """
        Возвращает проект по ID.
        Args:
            project_id: ID проекта.
            user_id: ID текущего пользователя.

        Returns:
            dict: информация о проекте.
        """

        logger.debug(f'Запрос проекта {project_id} для пользователя {user_id}')
        return self._request('GET', f'/projects/{project_id}', 
                             params={'user_id': user_id})

    def add_project(self, data: dict, user_id: int) -> dict:
        """
         Создаёт проект.
        Args:
            data: должен содержать поля ProjectCreate.
            user_id: ID текущего пользователя.

        Returns:
            dict: созданный проект.
        """

        logger.info(f'Создание проекта пользователем {user_id}')
        return self._request('POST', '/projects/', params={'user_id': user_id}, data=data)

    def update_project(self, project_id: int, data: dict, user_id: int) -> dict:
        """
        Обновляет проект.
        Args:
            project_id: ID проекта.
            data: поля и данные, которые нужно изменить.
            user_id: ID пользователя.

        Returns:
            dict: измененный проект.
        """

        logger.info(f'Обновление проекта {project_id} пользователем {user_id}')
        return self._request('PUT', f'/projects/{project_id}', params={'user_id': user_id}, data=data)

    def delete_project(self, project_id: int, user_id: int) -> dict:
        """
        Удаляет проект.
        Args:
            project_id: ID проекта.
            user_id: ID пользователя.

        Returns:
            dict: 'success': True, если успешно удалено, иначе придет ошибка
        """

        logger.info(f'Удаление проекта {project_id} пользователем {user_id}')
        return self._request('DELETE', f'/projects/{project_id}', params={'user_id': user_id})

    def toggle_project_favorite(self, project_id: int) -> dict:
        """
        Переключает избранное проекта.
        Args:
            project_id: ID проекта.

        Returns:
            dict: обновлённый проект с новым значением is_favorite.
        """

        logger.info(f'Переключение избранного для проекта {project_id}')
        return self._request('POST', f'/projects/{project_id}/favorite')

    def toggle_project_private(self, project_id: int, user_id: int) -> dict:
        """
        Переключает приватность проекта.
        Args:
            project_id: ID проекта.
            user_id: ID текущего пользователя. 

        Returns:
            dict: обновлённый проект с новым значением is_private.
        """

        logger.info(f'Переключение приватности проекта {project_id} пользователем {user_id}')
        return self._request('POST', f'/projects/{project_id}/toggle-private',
                             params={'user_id': user_id})

    def search_projects(self, query: str, user_id: int) -> list[dict]:
        """
        Поиск проектов по тексту.
        Args:
            query: запрос на поиск.
            user_id: ID текущего пользователя. 

        Returns:
            list[dict]: список проектов, соответствующих запросу.
        """

        logger.debug(f'Поиск проектов по запросу "{query}" для пользователя {user_id}')
        return self._request('GET', '/projects/search/', params={'q': query, 'user_id': user_id})

    # ---------- Задачи ----------
    def get_tasks(self, project_id: int, user_id: int, include_archived: bool = False) -> list[dict]:
        """
        Возвращает задачи проекта.
        Args:
            project_id: ID проекта.
            user_id: ID текущего пользователя. 
            include_archived: True, если нужно включить архивные задачи.

        Returns:
            list[dict]: список задач, отсортированных по статусу и избранному.
        """
        logger.debug(f'Запрос задач проекта {project_id} для пользователя {user_id}, '
                     f'include_archived={include_archived}')
        return self._request('GET', '/tasks/',
                             params={'project_id': project_id, 'user_id': user_id,
                                     'include_archived': str(include_archived).lower()})

    def get_task_by_id(self, task_id: int, user_id: int) -> dict:
        """
        Возвращает задачу по ID.
        Args:
            task_id: ID задачи. 
            user_id: ID текущего пользователя. 

        Returns:
            dict: объект задачи.
        """

        logger.debug(f'Запрос задачи {task_id} для пользователя {user_id}')
        return self._request('GET', f'/tasks/{task_id}', params={'user_id': user_id})

    def add_task(self, data: dict, user_id: int) -> dict:
        """
        Создаёт задачу. data должен содержать поля TaskCreate.
        Args:
            data: поля, которые нужно заполнит при создании.
            user_id: ID текущего пользователя. 

        Returns:
            dict: созданная задача с ID и датами.
        """

        logger.info(f'Создание задачи в проекте {data.get('project_id')} пользователем {user_id}')
        return self._request('POST', '/tasks/', params={'user_id': user_id}, data=data)

    def update_task(self, task_id: int, data: dict, user_id: int) -> dict:
        """
        Обновляет задачу.
        Args:
            task_id: ID задачи. 
            data: поля, которые нужно обновить.
            user_id: ID текущего пользователя. 

        Returns:
            dict: обновлённая задача.
        """

        logger.info(f'Обновление задачи {task_id} пользователем {user_id}')
        return self._request('PUT', f'/tasks/{task_id}', params={'user_id': user_id}, data=data)

    def delete_task(self, task_id: int, user_id: int, delete_children: bool = False) -> dict:
        """
        Удаляет задачу.
        Args:
            task_id: ID задачи. 
            user_id: ID текущего пользователя. 
            delete_children: True, если нужно удалить подзадачи.

        Returns:
            dict: {'success': True} при успехе.
        """

        logger.info(f'Удаление задачи {task_id} пользователем {user_id}, delete_children={delete_children}')
        return self._request('DELETE', f'/tasks/{task_id}',
                             params={'user_id': user_id, 'delete_children': str(delete_children).lower()})

    def toggle_task_favorite(self, user_id: int, task_id: int) -> dict:
        """
        Переключает избранное задачи.
        Args:
            task_id: ID задачи.
            user_id: ID пользователя.

        Returns:
            dict: обновлённая задача с новым значением is_favorite.
        """

        logger.info(f'Переключение избранного для задачи {task_id} пользователем {user_id}')
        return self._request('POST', f'/tasks/{task_id}/favorite', params={'user_id': user_id})

    def toggle_task_private(self, task_id: int, user_id: int) -> dict:
        """
        Переключает приватность задачи.
        Args:
            task_id: ID задачи. 
            user_id: ID текущего пользователя. 

        Returns:
            dict: обновлённая задача с новым значением is_private.
        """

        logger.info(f'Переключение приватности задачи {task_id} пользователем {user_id}')
        return self._request('POST', f'/tasks/{task_id}/toggle-private', params={'user_id': user_id})

    def archive_subtree(self, task_id: int, user_id: int) -> dict:
        """
        Архивирует поддерево задач.
        Args:
            task_id: ID задачи.
            user_id: ID текущего пользователя. 

        Returns:
            dict: archived_count - количество архивированных задач
        """

        logger.info(f'Архивация поддерева задачи {task_id} пользователем {user_id}')
        return self._request('POST', f'/tasks/{task_id}/archive', params={'user_id': user_id})

    def unarchive_subtree(self, task_id: int, user_id: int) -> dict:
        """
        Восстанавливает поддерево задач.
        Args:
            task_id: ID задачи. 
            user_id: ID текущего пользователя. 

        Returns:
            dict: unarchived_count - количество разархивированных задач
        """

        logger.info(f'Восстановление поддерева задачи {task_id} пользователем {user_id}')
        return self._request('POST', f'/tasks/{task_id}/unarchive', params={'user_id': user_id})

    def change_task_status(self, task_id: int, new_status: str, user_id: int) -> dict:
        """
        Меняет статус задачи.
        Args:
            task_id: ID задачи.
            new_status: новый статус задачи.
            user_id: ID текущего пользователя. 

        Returns:
            dict: измененная задача.
        """

        logger.info(f'Изменение статуса задачи {task_id} на "{new_status}" пользователем {user_id}')
        return self._request('POST', f'/tasks/{task_id}/status',
                             params={'new_status': new_status, 'user_id': user_id})
