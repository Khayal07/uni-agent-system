from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from . import crud, schemas, models
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="UniAgent System API")

# DB Bağlantı Dependency-si
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/universities/", response_model=schemas.University)
def create_university(university: schemas.UniversityCreate, db: Session = Depends(get_db)):
    return crud.create_university(db=db, university=university)

@app.get("/universities/", response_model=List[schemas.University])
def read_universities(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_universities(db, skip=skip, limit=limit)

@app.post("/programs/", response_model=schemas.Program)
def create_program(program: schemas.ProgramCreate, db: Session = Depends(get_db)):
    return crud.create_program(db=db, program=program)