from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

# --- University Schemas ---
class UniversityBase(BaseModel):
    name: str
    website_url: Optional[str] = None

class UniversityCreate(UniversityBase):
    pass

class University(UniversityBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Program Schemas ---
class ProgramBase(BaseModel):
    faculty: str
    program_name: str
    degree: str
    language: str
    tuition_fee: Optional[str] = None
    requirements: Optional[str] = None

class ProgramCreate(ProgramBase):
    university_id: int

class Program(ProgramBase):
    id: int
    university_id: int
    extracted_at: datetime

    class Config:
        from_attributes = True