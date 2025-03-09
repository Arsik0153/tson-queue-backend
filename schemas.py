from pydantic import BaseModel
from datetime import datetime

class DepartmentBase(BaseModel):
    name: str

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

class AppointmentCreate(AppointmentBase):
    pass

class Appointment(AppointmentBase):
    id: int
    is_booked: bool
    class Config:
        from_attributes = True