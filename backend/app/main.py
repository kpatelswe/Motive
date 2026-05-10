from fastapi import FastAPI

from app.routers import auth, hangouts

app = FastAPI(title="Motive")

app.include_router(auth.router)
app.include_router(hangouts.router)

@app.get("/")
def root():
    return {"message": "Motive backend running"}
