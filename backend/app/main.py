from fastapi import FastAPI

app = FastAPI(title="University Data Intelligence Agent API")

@app.get("/")
def read_root():
    return {"status": "Sistem aktivdir", "project": "University Data Intelligence Agent"}