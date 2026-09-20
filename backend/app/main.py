from fastapi import FastAPI

from .api.routes import router

app = FastAPI(title="Project Brain")
app.include_router(router)
