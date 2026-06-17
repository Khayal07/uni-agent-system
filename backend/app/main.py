from fastapi import FastAPI
from .database import engine
from . import models

# FastAPI işə düşəndə cədvəlləri avtomatik bazada yaradır
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="University Data Intelligence Agent API")

@app.get("/")
def read_root():
    return {"status": "Sistem aktivdir", "project": "University Data Intelligence Agent"}