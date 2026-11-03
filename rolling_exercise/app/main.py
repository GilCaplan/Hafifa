from fastapi import FastAPI

from app.api.handlers import register_handlers
from app.api.routes import router
from app.core.logs import setup_logging

setup_logging()

app = FastAPI()
register_handlers(app)
app.include_router(router)
