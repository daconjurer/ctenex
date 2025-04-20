from fastapi import FastAPI
from loguru import logger

from ctenex.api.app_factory import create_app
from ctenex.api.controllers.status import router as status_router
from ctenex.api.v1.in_memory.controllers.exchange import router as exchange_router
from ctenex.api.v1.in_memory.lifespan import lifespan
from ctenex.settings.application import get_app_settings

settings = get_app_settings()

app = FastAPI()

stateful_app = create_app(
    lifespan=lifespan,
    routers=[status_router, exchange_router],
)

app.mount("/v1/stateful", stateful_app)


def main():
    _reload = settings.environment == "dev"
    logger.info(f"Running in {settings.environment} mode")

    uvicorn.run(
        app="ctenex.api.main:stateful_app",
        host=str(settings.api.api_host),
        port=settings.api.api_port,
        reload=_reload,
    )


if __name__ == "__main__":
    import uvicorn

    main()
