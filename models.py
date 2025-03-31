from sqlalchemy import Column, Integer, String, DateTime, Boolean, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String)
    
    appointments = relationship("Appointment", back_populates="department")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), index=True)
    time_slot = Column(DateTime)
    user_name = Column(String)
    phone_number = Column(String)
    status = Column(String, default="active")  # possible values: active, cancelled
    
    department = relationship("Department", back_populates="appointments")
    
    __table_args__ = (
        UniqueConstraint('department_id', 'time_slot', name='uix_department_timeslot'),
    )