from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional
import datetime_utils

class DepartmentBase(BaseModel):
    name: str
    address: str
    is_special: bool

class DepartmentCreate(DepartmentBase):
    pass

class Department(DepartmentBase):
    id: int
    class Config:
        from_attributes = True

class AppointmentBase(BaseModel):
    department_id: int
    time_slot: datetime
    user_name: str
    phone_number: str
    iin: str = Field(..., min_length=12, max_length=12, pattern=r'^\d{12}$')
    service: str
    
    @validator('time_slot', pre=True)
    def parse_time_slot(cls, value):
        """Parse string datetime to datetime object if it's a string"""
        if isinstance(value, str):
            return datetime_utils.parse_datetime(value)
        return value

class AppointmentCreate(AppointmentBase):
    pass

class Appointment(AppointmentBase):
    id: int
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class AppointmentResponse(Appointment):
    department_name: str
    department_address: str
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class DepartmentWithStats(Department):
    total_appointments: int
    today_appointments: int
    class Config:
        from_attributes = True

class ServiceList(BaseModel):
    services: list[str]