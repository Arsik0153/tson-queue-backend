import pytz
from sqlalchemy import Column, Integer, String, DateTime, Boolean, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime

# Define Almaty timezone
almaty_tz = pytz.timezone('Asia/Almaty')

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String)
    is_special = Column(Boolean, default=False) # Added field to distinguish Special TSON
    
    appointments = relationship("Appointment", back_populates="department")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"))
    # Store datetime without timezone info for simplicity
    time_slot = Column(DateTime, index=True)
    user_name = Column(String, index=True)
    phone_number = Column(String)
    iin = Column(String, index=True, nullable=False)
    service = Column(String, nullable=False)
    status = Column(String, default="active")  # possible values: active, cancelled
    
    department = relationship("Department", back_populates="appointments")
    
    __table_args__ = (
        UniqueConstraint('department_id', 'time_slot', name='uix_department_timeslot'),
    )

    # Set default timestamp with Almaty timezone
    # created_at = Column(DateTime(timezone=True), server_default=func.now()) # Consider adding creation timestamp

    # Ensure time_slot is stored in UTC but represents Almaty time intention
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     if self.time_slot and self.time_slot.tzinfo is None:
    #          # Assume naive datetime is Almaty time, convert to UTC for storage
    #         self.time_slot = almaty_tz.localize(self.time_slot).astimezone(pytz.utc)
    #     elif self.time_slot:
    #         # Ensure it's UTC if timezone is already provided
    #         self.time_slot = self.time_slot.astimezone(pytz.utc)