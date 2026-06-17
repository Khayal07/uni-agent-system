from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class University(Base):
    __tablename__ = "universities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    website_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Əlaqələr (Relationships)
    pages = relationship("ScrapedPage", back_populates="university", cascade="all, delete-orphan")
    programs = relationship("Program", back_populates="university", cascade="all, delete-orphan")


class ScrapedPage(Base):
    __tablename__ = "scraped_pages"

    id = Column(Integer, primary_key=True, index=True)
    university_id = Column(Integer, ForeignKey("universities.id"))
    url = Column(String, nullable=False)
    raw_html = Column(Text, nullable=True)  # Skrap olunmuş xam kontent
    scraped_at = Column(DateTime, default=datetime.utcnow)

    university = relationship("University", back_populates="pages")


class Program(Base):
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, index=True)
    university_id = Column(Integer, ForeignKey("universities.id"))
    faculty = Column(String, nullable=True)      # Məs: İnformasiya Texnologiyaları
    program_name = Column(String, nullable=False) # Məs: Süni İntellekt Mühəndisliyi
    degree = Column(String, nullable=True)       # Bachelor, Master, PhD
    language = Column(String, nullable=True)     # English, Azerbaijani və s.
    tuition_fee = Column(String, nullable=True)  # Təhsil haqqı qiyməti
    requirements = Column(Text, nullable=True)   # Qəbul şərtləri (TOEFL, GPA və s.)
    extracted_at = Column(DateTime, default=datetime.utcnow)

    university = relationship("University", back_populates="programs")