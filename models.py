from sqlalchemy import Column, Integer, String, Float, Date, DateTime
from sqlalchemy.sql import func
from database import Base


class Expense(Base):
    __tablename__='expenses'

    id=Column(Integer,primary_key=True,index=True)
    category=Column(String,nullable=False)
    amount=Column(Float,nullable=False)
    description=Column(String,nullable=True)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())