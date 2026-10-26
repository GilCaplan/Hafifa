import uvicorn

from air_quality_api.const import App, settings


class Server:
    # Make Server a Singelton.
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def run(self) -> None:
        uvicorn.run(App.IMPORT_PATH, host=settings.host, port=settings.port, reload=settings.reload)


if __name__ == "__main__":
    Server().run()
