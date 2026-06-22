from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from database import Base
from datetime import datetime
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True, index=True )
    email = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)



class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True )
    user_id = Column(Integer, ForeignKey("users.id"))
    file_path = Column(String)
    extracted_text = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="resumes")
    questions = relationship("Question", back_populates="resumes")


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resume.id"))
    question_text = Column(Text)
    category = Column(String, nullable=True)
    
    resume = relationship("Resume", back_populates="questions")




