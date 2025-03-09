from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models, schemas, crud
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Главная страница (просто заглушка для API)
@app.get("/")
def read_root():
    return {"message": "Добро пожаловать в API для записи в ЦОН"}

# Получить список отделений
@app.get("/departments/", response_model=list[schemas.Department])
def get_departments(db: Session = Depends(get_db)):
    return crud.get_departments(db)

# Получить свободные слоты для отделения
@app.get("/appointments/{department_id}/available/", response_model=list[schemas.Appointment])
def get_available_slots(department_id: int, db: Session = Depends(get_db)):
    slots = crud.get_available_slots(db, department_id)
    if not slots:
        raise HTTPException(status_code=404, detail="Нет свободных слотов")
    return slots

# Создать запись
@app.post("/appointments/", response_model=schemas.Appointment)
def create_appointment(appointment: schemas.AppointmentCreate, db: Session = Depends(get_db)):
    # Проверка, свободен ли слот
    existing = db.query(models.Appointment).filter(
        models.Appointment.time_slot == appointment.time_slot,
        models.Appointment.department_id == appointment.department_id
    ).first()
    if existing and existing.is_booked:
        raise HTTPException(status_code=400, detail="Этот слот уже занят")
    return crud.create_appointment(db, appointment)

# Админ-панель (заглушка с базовой авторизацией)
@app.get("/admin/statistics/")
def get_statistics(db: Session = Depends(get_db), username: str = "admin", password: str = "password"):
    if username != "admin" or password != "password":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль"
        )
    appointments = db.query(models.Appointment).all()
    return {"total_appointments": len(appointments)}