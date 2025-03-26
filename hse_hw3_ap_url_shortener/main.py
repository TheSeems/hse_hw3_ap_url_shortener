import logging
from contextlib import asynccontextmanager, AsyncExitStack

import uvicorn
from fastapi import FastAPI
from fastapi.dependencies.utils import get_dependant, solve_dependencies
from starlette.requests import Request

from hse_hw3_ap_url_shortener.db import create_db_and_tables, EngineDep
from hse_hw3_ap_url_shortener.endpoints.auth import auth_router
from hse_hw3_ap_url_shortener.endpoints.link import links_router
from hse_hw3_ap_url_shortener.service.cleanup import CleanupServiceDep
from hse_hw3_ap_url_shortener.service.populate_cache import PopulateCacheServiceDep

logging.basicConfig(level=logging.INFO)


# Borrowed from https://github.com/fastapi/fastapi/discussions/11742
def solve_lifespan(lifespan):
    @asynccontextmanager
    async def _solve_lifespan(app: FastAPI):
        # A fake request for solve_dependencies
        request = Request(
            scope={
                "type": "http",
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": "/",
                "raw_path": b"/",
                "query_string": b"",
                "root_path": "",
                "headers": ((b"X-Request-Scope", b"lifespan"),),
                "client": ("localhost", 80),
                "server": ("localhost", 80),
                "state": app.state,
            }
        )
        dependant = get_dependant(path="/", call=lifespan)

        async with AsyncExitStack() as async_exit_stack:
            solved_deps = await solve_dependencies(
                request=request,
                dependant=dependant,
                async_exit_stack=async_exit_stack,
                embed_body_fields=False,
            )

            ctxmgr = asynccontextmanager(lifespan)
            async with ctxmgr(**solved_deps.values) as value:
                yield value

    return _solve_lifespan


@solve_lifespan
async def lifespan(
    engine: EngineDep,
    cleanup_service: CleanupServiceDep,
    populate_cache_service: PopulateCacheServiceDep,
):
    create_db_and_tables(engine)
    cleanup_service.start_scheduler()
    populate_cache_service.start_scheduler()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)
app.include_router(links_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
