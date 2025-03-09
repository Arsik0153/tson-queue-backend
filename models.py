from sqlalchemy import Column, Integer, String, DateTime, Boolean, UniqueConstraint
from database import Base

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String)

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, index=True)
    time_slot = Column(DateTime)
    user_name = Column(String)
    phone_number = Column(String)
    
    __table_args__ = (UniqueConstraint('department_id', 'time_slot', name='_department_timeslot_uc'),)
    
    __table_args__ = (
        UniqueConstraint('department_id', 'time_slot', name='uix_department_timeslot'),
    )