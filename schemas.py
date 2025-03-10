from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DepartmentBase(BaseModel):
    name: str
    address: str

class DepartmentCreate(DepartmentBase):
    pass

class Department(DepartmentBase):
    id: int
    class Config:
        from_attributes = True

class AppointmentBase(BaseModel):
    department_id: int
    time_slot: datetime
    user_name: Optional[str] = None
    phone_number: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    pass

class Appointment(AppointmentBase):
    id: int
    class Config:
        from_attributes = True

class AppointmentResponse(Appointment):
    department_name: str
    department_address: str
    class Config:
        from_attributes = True