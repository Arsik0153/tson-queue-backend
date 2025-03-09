from sqlalchemy.orm import Session
import models, schemas

def get_departments(db: Session):
    return db.query(models.Department).all()

def get_available_slots(db: Session, department_id: int):
    return db.query(models.Appointment).filter(
        models.Appointment.department_id == department_id,
        models.Appointment.is_booked == False
    ).all()

def create_appointment(db: Session, appointment: schemas.AppointmentCreate):
    db_appointment = models.Appointment(**appointment.dict(), is_booked=True)
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment