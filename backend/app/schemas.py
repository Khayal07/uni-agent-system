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
    faculty: Optional[str] = None
    program_name: str
    degree: Optional[str] = None
    language: Optional[str] = None
    tuition_fee: Optional[str] = None
    requirements: Optional[str] = None
    application_deadline: Optional[str] = None
    gpa_requirement: Optional[str] = None
    documents_required: Optional[str] = None

class ProgramCreate(ProgramBase):
    university_id: int

class Program(ProgramBase):
    id: int
    university_id: int
    extracted_at: datetime
    confidence_score: Optional[float] = None
    field_confidence: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


# --- ChangeLog Schema ---
class ChangeLog(BaseModel):
    id: int
    program_id: Optional[int] = None
    university_id: int
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    detected_at: datetime

    class Config:
        from_attributes = True