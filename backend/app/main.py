from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine
from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Motive", lifespan=lifespan)


@app.get("/")
def root():
    return {"message": "Motive backend running"}
