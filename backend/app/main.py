import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .background import staleness_sweep_loop
from .config import CORS_ORIGINS


@asynccontextmanager
async def lifespan(app: FastAPI):
    sweep_task = asyncio.create_task(staleness_sweep_loop())
    yield
    sweep_task.cancel()


app = FastAPI(title="Project Brain", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)
app.include_router(router)
