import uvicorn

from air_quality_api.const import APP_PATH, HOST, PORT, RELOAD


class Server:
    # Make Server a Singelton.
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def run(self) -> None:
        uvicorn.run(APP_PATH, host=HOST, port=PORT, reload=RELOAD)


if __name__ == "__main__":
    Server().run()
