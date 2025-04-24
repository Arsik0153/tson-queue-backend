from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from datetime import datetime, timedelta, time
import models, schemas
import datetime_utils
from config import settings

def get_departments(db: Session):
    return db.query(models.Department).all()

def get_department_by_id(db: Session, department_id: int):
    return db.query(models.Department).filter(models.Department.id == department_id).first()

def get_booked_slots(db: Session, department_id: int):
    return db.query(models.Appointment).filter(
        models.Appointment.department_id == department_id
    ).all()

def create_appointment(db: Session, appointment: schemas.AppointmentCreate):
    # No timezone conversion needed - store as naive datetime
    db_appointment = models.Appointment(
        department_id=appointment.department_id,
        time_slot=appointment.time_slot,  # Store as naive datetime
        user_name=appointment.user_name,
        phone_number=appointment.phone_number,
        iin=appointment.iin,
        service=appointment.service
    )
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

def get_appointment_by_id(db: Session, appointment_id: int):
    appointment = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if appointment:
        # Add department details to the appointment object
        appointment.department_name = appointment.department.name
        appointment.department_address = appointment.department.address
    return appointment

# --- Logic for Available Slots ---
def get_available_slots(db: Session, department_id: int, target_date: datetime.date):
    # 1. Define all possible slots for the target date within working hours
    all_possible_slots = datetime_utils.get_working_slots_for_date(target_date)
    
    # 2. Get booked slots for that department and date
    start_time, end_time = datetime_utils.get_date_range_bounds(target_date)
    
    # Get all appointments for this department and date
    booked_appointments = db.query(models.Appointment).filter(
        models.Appointment.department_id == department_id,
        models.Appointment.time_slot >= start_time,
        models.Appointment.time_slot < end_time
    ).all()
    
    # Create a list of booked datetime objects
    booked_slots = [appt.time_slot for appt in booked_appointments]
    
    # Make a clean list of available slots by checking each possible slot
    available_slots = []
    for slot in all_possible_slots:
        if slot not in booked_slots:
            available_slots.append(slot)
    
    return available_slots

# --- Service List Logic ---
REGULAR_TSON_SERVICES = [
    "Консультация",
    "Услуги НПЦЗем",
    "Нәтиже",
    "Социальные услуги",
    "Льготные категории",
    "Выдача документов",
]

SPECIAL_TSON_SERVICES = [
    "Механика B",
    "Категории D,E,A,D1",
    "Категория C1",
    "Категория C",
    "B автомат",
    "Осмотр ТС",
    "Регистрация (перерегистрация) ТС",
    "СРТС и доверенности",
    "Водительское удостоверение",
    "Льготное окно ВУ",
    "Выдача СРТС",
]

def get_services_for_department(db: Session, department_id: int) -> list[str]:
    department = get_department_by_id(db, department_id)
    if not department:
        return [] # Or raise HTTPException if preferred

    if department.is_special:
        return SPECIAL_TSON_SERVICES
    else:
        return REGULAR_TSON_SERVICES