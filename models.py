from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from database import Base
from datetime import datetime
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True )
    email = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    resumes = relationship("Resume", back_populates="user")



class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True )
    user_id = Column(Integer, ForeignKey("users.id"))
    file_path = Column(String)
    extracted_text = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="resumes")
    questions = relationship("Question", back_populates="resume")


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    question_text = Column(Text)
    category = Column(String, nullable=True)
    
    resume = relationship("Resume", back_populates="questions")

class InterviewSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    created_at = Column(DateTime, default=datetime.utcnow)





