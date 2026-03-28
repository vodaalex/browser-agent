import uvicorn

from app.config import settings


def main():
    uvicorn.run(
        "app.server.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()

