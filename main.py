from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from fastapi.middleware.cors import CORSMiddleware

import models, schemas, crud
from database import engine, get_db
from auth import create_access_token, get_current_admin
from config import settings

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ЦОН API", description="API для онлайн-записи в ЦОН")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Главная страница (просто заглушка для API)
@app.get("/")
def read_root():
    return {"message": "Добро пожаловать в API для записи в ЦОН"}

# Получить список отделений
@app.get("/departments/", response_model=list[schemas.Department])
def get_departments(db: Session = Depends(get_db)):
    return crud.get_departments(db)

# Получить запись по ID
@app.get("/appointments/{appointment_id}", response_model=schemas.AppointmentResponse)
def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appointment = crud.get_appointment_by_id(db, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return appointment

# Получить свободные слоты для отделения
@app.get("/appointments/{department_id}/available/", response_model=list[schemas.Appointment])
def get_booked_slots(department_id: int, db: Session = Depends(get_db)):
    slots = crud.get_booked_slots(db, department_id)
    return slots

# Создать запись
@app.post("/appointments/", response_model=schemas.Appointment)
def create_appointment(appointment: schemas.AppointmentCreate, db: Session = Depends(get_db)):
    # Convert UTC time to Almaty time (UTC+6)
    almaty_time = appointment.time_slot + timedelta(hours=6)
    
    # Validate business hours (9:00 to 18:00 Almaty time)
    hour = almaty_time.hour
    print(hour)
    if hour < 9 or hour >= 18:
        raise HTTPException(status_code=400, detail="Записаться можно только с 9:00 утра до 18:00 по времени Алматы")
    
    # Check if slot is already booked
    existing = db.query(models.Appointment).filter(
        models.Appointment.time_slot == appointment.time_slot,
        models.Appointment.department_id == appointment.department_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Это время уже занято")
    
    # Create new appointment
    return crud.create_appointment(db, appointment)

# Endpoint для получения JWT токена
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != settings.ADMIN_USERNAME or form_data.password != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Защищенная админ-панель со статистикой
@app.get("/admin/statistics/")
def get_statistics(db: Session = Depends(get_db), current_admin: str = Depends(get_current_admin)):
    appointments = db.query(models.Appointment).all()
    departments = db.query(models.Department).all()
    
    # Get total appointments
    total_appointments = len(appointments)
    
    # Get appointments by department
    appointments_by_department = {}
    for dept in departments:
        dept_appointments = len([a for a in appointments if a.department_id == dept.id])
        appointments_by_department[dept.name] = dept_appointments
    
    return {
        "total_appointments": total_appointments,
        "appointments_by_department": appointments_by_department
    }
    booked_appointments = len([a for a in appointments if a.is_booked])
    return {
        "total_appointments": total_appointments,
        "booked_appointments": booked_appointments,
        "available_appointments": total_appointments - booked_appointments
    }