from fastapi import FastAPI

app = FastAPI(title="Motive")

@app.get("/")
def root():
    return {"message": "Motive backend running"}
