import sys
import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import settings
from server.api import router
from server.database import init_db
from server.logger import setup_logging

logger = logging.getLogger('Server_MAIN')

if __name__ == '__main__':
    try:
        setup_logging()
        app = FastAPI(
            title='DevKeeper Network API',
            description='Сервер для совместной работы над проектами и задачами',
            version='1.0'
        )

        # Настройка CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*'],
        )

        # Подключаем роутер
        app.include_router(router, prefix='/api')

        @app.get('/')
        def root():
            return {'message': 'DevKeeper Server is running'}

        init_db()

        host = settings.SERVER_HOST
        port = settings.SERVER_PORT

        if len(sys.argv) > 1:
            args = sys.argv[1:]
            for i, arg in enumerate(args):
                if arg == '--host' and i + 1 < len(args):
                    host = args[i + 1]
                elif arg == '--port' and i + 1 < len(args):
                    port = int(args[i + 1])

            # Выводим информацию о запуске
        print("=" * 50)
        print(f"DevKeeper Server запущен")
        print(f"Локальный IP (для подключения с других устройств): {settings.local_ip}")
        print(f"Порт: {port}")
        print(f"URL для клиента: http://{settings.local_ip}:{port}/api")
        print("=" * 50)

        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=False
        )
    except Exception as e:
        print(f"❌ Ошибка при запуске сервера: {e}")
        logging.error(f"Ошибка запуска сервера: {e}", exc_info=True)
        print("Нажмите Enter для выхода...")
        input()
