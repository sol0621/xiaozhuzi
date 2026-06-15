from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class HomeworkRecord(Base):
    __tablename__ = "homework_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    grade = Column(Integer, nullable=False)
    subject = Column(String(20), nullable=False)
    mode = Column(String(20), nullable=False)
    total_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    wrong_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

class ProblemRecord(Base):
    __tablename__ = "problem_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    homework_id = Column(Integer, nullable=False)
    question_content = Column(Text)
    is_correct = Column(Integer, default=1)
    wrong_reason = Column(Text)
    error_type = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
