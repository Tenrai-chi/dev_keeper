import sys
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import settings
from server.api import router
from server.database import init_db
from server.logger import setup_logging

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


if __name__ == '__main__':
    setup_logging()
    init_db()
    host = sys.argv[1] if len(sys.argv) > 1 else settings.SERVER_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else settings.SERVER_PORT
    uvicorn.run(
        'server.main:app',
        host=host,
        port=port,
        reload=False
    )
