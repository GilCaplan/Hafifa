from typing import Self

import uvicorn

from app.core.config import settings
from app.core.constants import Consts


class Server:
    _instance = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def run(self) -> None:
        # The app's middleware logs every request (with its duration), so uvicorn's access log would repeat it
        uvicorn.run(Consts.app_path, host=settings.host, port=settings.port, reload=settings.reload, access_log=False)


if __name__ == "__main__":
    Server().run()
