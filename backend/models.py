from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"))
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class TeeTime(Base):
    __tablename__ = "tee_times"
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, index=True)
    course_name = Column(String)
    date = Column(String, index=True)
    time_minutes = Column(Integer)  # minutes from midnight
    time_display = Column(String)   # "10:00 AM"
    available = Column(Boolean, default=True)
    scraped_at = Column(DateTime)

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True)
    club_id = Column(Integer, unique=True)
    name = Column(String)

Base.metadata.create_all(engine)
