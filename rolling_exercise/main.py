import uvicorn
from fastapi.staticfiles import StaticFiles

from air_quality_api.api import app
from air_quality_api.const import APP_PATH, FRONTEND_DIR, FRONTEND_ROUTE, HOST, PORT, RELOAD

# Mounted after the API routes are registered, so it only serves paths that no API route matched.
app.mount(FRONTEND_ROUTE, StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


class Server:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def run(self) -> None:
        uvicorn.run(APP_PATH, host=HOST, port=PORT, reload=RELOAD)


if __name__ == "__main__":
    Server().run()
