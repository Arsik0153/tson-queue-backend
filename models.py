from sqlalchemy import Column, Integer, String, DateTime, Boolean
from database import Base

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, index=True)
    time_slot = Column(DateTime, unique=True)
    user_name = Column(String)
    is_booked = Column(Boolean, default=False)