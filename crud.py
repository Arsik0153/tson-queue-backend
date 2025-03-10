from sqlalchemy.orm import Session
import models, schemas

def get_departments(db: Session):
    return db.query(models.Department).all()

def get_booked_slots(db: Session, department_id: int):
    return db.query(models.Appointment).filter(
        models.Appointment.department_id == department_id
    ).all()

def create_appointment(db: Session, appointment: schemas.AppointmentCreate):
    db_appointment = models.Appointment(**appointment.dict())
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