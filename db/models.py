"""ORM models."""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    grade = Column(String, nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "subject": self.subject,
                "score": self.score, "grade": self.grade}
