from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, date, time
from fastapi.middleware.cors import CORSMiddleware
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from typing import Optional
import sqlalchemy.exc

import models, schemas, crud
from database import engine, get_db
from auth import create_access_token, get_current_admin
from config import settings
from datetime import datetime, timedelta
import datetime_utils

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

# Register the font before creating the PDF
pdfmetrics.registerFont(TTFont('ArialUnicodeMS', 'fonts/ArialUnicodeMS.ttf'))
# pdfmetrics.registerFont(TTFont('ArialUnicodeMS-Bold', 'fonts/ArialUnicodeMS-Bold.ttf'))

# Create custom styles with Cyrillic support
def get_custom_styles():
    styles = getSampleStyleSheet()
    # Create custom styles with Cyrillic font
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontName='ArialUnicodeMS',
        fontSize=24,
        spaceAfter=30
    ))
    styles.add(ParagraphStyle(
        name='CustomHeading1',
        parent=styles['Heading1'],
        fontName='ArialUnicodeMS',
        fontSize=18,
        spaceAfter=20
    ))
    styles.add(ParagraphStyle(
        name='CustomNormal',
        parent=styles['Normal'],
        fontName='ArialUnicodeMS',
        fontSize=12,
        spaceAfter=12
    ))
    return styles

# Главная страница (просто заглушка для API)
@app.get("/")
def read_root():
    return {"message": "Добро пожаловать в API для записи в ЦОН"}

# Получить список отделений (includes is_special)
@app.get("/departments/", response_model=list[schemas.Department])
def get_departments(db: Session = Depends(get_db)):
    return crud.get_departments(db) # crud function needs to return the model object

# Получить список услуг для отделения
@app.get("/departments/{department_id}/services/", response_model=schemas.ServiceList)
def get_department_services(department_id: int, db: Session = Depends(get_db)):
    services = crud.get_services_for_department(db, department_id)
    if not services:
        # Check if department exists before returning empty list
        department = crud.get_department_by_id(db, department_id)
        if not department:
            raise HTTPException(status_code=404, detail="Отделение не найдено")
    return schemas.ServiceList(services=services)

# Получить запись по ID (includes iin and service)
@app.get("/appointments/{appointment_id}", response_model=schemas.AppointmentResponse)
def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appointment = crud.get_appointment_by_id(db, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    # No need to convert timezones
    return schemas.AppointmentResponse(
        id=appointment.id,
        department_id=appointment.department_id,
        time_slot=appointment.time_slot,
        user_name=appointment.user_name,
        phone_number=appointment.phone_number,
        iin=appointment.iin,
        service=appointment.service,
        department_name=appointment.department.name,
        department_address=appointment.department.address
    )

# Получить свободные слоты для отделения
@app.get("/appointments/{department_id}/available/", response_model=list[schemas.Appointment])
def get_booked_slots(department_id: int, db: Session = Depends(get_db)):
    slots = crud.get_booked_slots(db, department_id)
    return slots

# --- Updated Endpoint: Get AVAILABLE Slots ---
@app.get("/departments/{department_id}/available_slots/", response_model=list[datetime])
def get_available_slots_for_department(
    department_id: int,
    date_str: str = Query(..., description="Date in YYYY-MM-DD format"), # Require date
    db: Session = Depends(get_db)
):
    try:
        target_date = datetime_utils.parse_date(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD.")

    # Check if department exists
    department = crud.get_department_by_id(db, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Отделение не найдено")

    # Prevent booking for past dates
    if datetime_utils.is_past_date(target_date):
        raise HTTPException(status_code=400, detail="Нельзя записаться на прошедшую дату.")

    available_slots = crud.get_available_slots(db, department_id, target_date)
    return available_slots 

# Создать запись (includes iin, service, and validation)
@app.post("/appointments/", response_model=schemas.Appointment)
def create_appointment(appointment: schemas.AppointmentCreate, db: Session = Depends(get_db)):
    # Fetch department to check its type and existence
    department = crud.get_department_by_id(db, appointment.department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Отделение не найдено")

    # Validate working hours
    if not datetime_utils.is_valid_working_hour(appointment.time_slot):
        raise HTTPException(status_code=400, detail="Записаться можно только с 9:00 утра до 18:00")

    # Validate selected service based on department type
    allowed_services = crud.get_services_for_department(db, appointment.department_id)
    if appointment.service not in allowed_services:
        raise HTTPException(status_code=400, detail=f"Неверная услуга '{appointment.service}' для данного отделения.")

    # Check if slot is already booked
    existing = db.query(models.Appointment).filter(
        models.Appointment.time_slot == appointment.time_slot,
        models.Appointment.department_id == appointment.department_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Это время уже занято")

    # Create new appointment
    try:
        return crud.create_appointment(db, appointment)
    except sqlalchemy.exc.IntegrityError:
        # This handles race conditions when two users book the same slot simultaneously
        db.rollback()
        raise HTTPException(status_code=400, detail="Это время уже занято")

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

# New dashboard statistics endpoint
@app.get("/admin/dashboard-statistics/general/")
def get_dashboard_statistics(db: Session = Depends(get_db), current_admin: str = Depends(get_current_admin)):
    # Get current date
    now = datetime.now()
    today = now.date()
    yesterday = today - timedelta(days=1)

    # Get today's range
    today_start, today_end = datetime_utils.get_date_range_bounds(today)
    yesterday_start, yesterday_end = datetime_utils.get_date_range_bounds(yesterday)

    # Get all appointments
    appointments = db.query(models.Appointment).all()
    departments = db.query(models.Department).all()

    # Total appointments
    total_appointments = len(appointments)

    # Today's appointments
    todays_appointments = db.query(models.Appointment).filter(
        models.Appointment.time_slot >= today_start,
        models.Appointment.time_slot < today_end
    ).count()

    # Yesterday's appointments (for +/- calculation)
    yesterdays_appointments = db.query(models.Appointment).filter(
        models.Appointment.time_slot >= yesterday_start,
        models.Appointment.time_slot < yesterday_end
    ).count()

    # Calculate load percentage
    # We'll consider 8 slots per day (9:00-17:00, 1 hour each) as 100% capacity
    slots_per_day = 8
    total_possible_slots = len(departments) * slots_per_day
    if total_possible_slots > 0:
        load_percentage = (todays_appointments / total_possible_slots) * 100
    else:
        load_percentage = 0

    return {
        "total_appointments": total_appointments,
        "today": {
            "count": todays_appointments,
            "difference_from_yesterday": todays_appointments - yesterdays_appointments
        },
        "cancelled_last_30_days": None,  # We don't have cancellation tracking in our current model
        "load_percentage": round(load_percentage, 1)
    }

# Get all appointments (admin only, with date filtering and new fields)
@app.get("/admin/appointments/", response_model=list[schemas.AppointmentResponse])
def get_all_appointments(
    db: Session = Depends(get_db),
    current_admin: str = Depends(get_current_admin),
    filter_date_str: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)")
):
    query = db.query(models.Appointment).join(models.Department)

    # Apply date filter if provided
    if filter_date_str:
        try:
            filter_date = datetime_utils.parse_date(filter_date_str)
            # Get date range bounds for filtering
            start_day, end_day = datetime_utils.get_date_range_bounds(filter_date)
            query = query.filter(
                models.Appointment.time_slot >= start_day,
                models.Appointment.time_slot < end_day
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты для фильтра. Используйте YYYY-MM-DD.")

    # Order by ID ascending (lowest first, highest last)
    appointments = query.order_by(models.Appointment.id.asc()).all()

    # Convert to response format with department info and new fields
    return [
        schemas.AppointmentResponse(
            id=appointment.id,
            department_id=appointment.department_id,
            time_slot=appointment.time_slot,
            user_name=appointment.user_name,
            phone_number=appointment.phone_number,
            iin=appointment.iin,
            service=appointment.service,
            department_name=appointment.department.name,
            department_address=appointment.department.address
        )
        for appointment in appointments
    ]

# Get all branches (admin only, includes is_special)
@app.get("/admin/branches/", response_model=list[schemas.DepartmentWithStats])
def get_all_branches(
    db: Session = Depends(get_db),
    current_admin: str = Depends(get_current_admin),
):
    # Get current date
    today = datetime.now().date()
    today_start, today_end = datetime_utils.get_date_range_bounds(today)

    # Get branches ordered by ID ascending (lowest first, highest last)
    branches = db.query(models.Department).order_by(models.Department.id.asc()).all()

    # Calculate statistics for each branch
    result = []
    for branch in branches:
        # Count total appointments for this branch
        total_appointments = db.query(func.count(models.Appointment.id)).filter(models.Appointment.department_id == branch.id).scalar() or 0

        # Count today's appointments
        today_appointments = db.query(func.count(models.Appointment.id)).filter(
            models.Appointment.department_id == branch.id,
            models.Appointment.time_slot >= today_start,
            models.Appointment.time_slot < today_end
        ).scalar() or 0

        # Create response with statistics
        branch_dict = {
            "id": branch.id,
            "name": branch.name,
            "address": branch.address,
            "is_special": branch.is_special,
            "total_appointments": total_appointments,
            "today_appointments": today_appointments
        }
        result.append(schemas.DepartmentWithStats(**branch_dict))

    return result

# Export route for generating PDF report (includes iin and service)
@app.get("/admin/export/")
def export_data(
    db: Session = Depends(get_db),
    current_admin: str = Depends(get_current_admin)
):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    elements = []
    styles = get_custom_styles()
    current_time = datetime.now()

    # Add Title and Date
    elements.append(Paragraph('ЦОН - Экспорт данных', styles['CustomTitle']))
    elements.append(Spacer(1, 10)) # Reduced spacer
    elements.append(Paragraph(f'Дата отчета: {current_time.strftime("%Y-%m-%d %H:%M:%S")}', styles['CustomNormal']))
    elements.append(Spacer(1, 20))

    # --- Branches Section ---
    elements.append(Paragraph('Отделения', styles['CustomHeading1']))
    elements.append(Spacer(1, 12))

    branches = db.query(models.Department).all()
    if branches:
        # Header row for branches
        branch_data = [['ID', 'Название', 'Тип', 'Адрес', 'Всего записей', 'Записей сегодня']]
        today = current_time.date()
        today_start, today_end = datetime_utils.get_date_range_bounds(today)

        for branch in branches:
            total_appts = db.query(func.count(models.Appointment.id)).filter(models.Appointment.department_id == branch.id).scalar() or 0
            today_appts = db.query(func.count(models.Appointment.id)).filter(
                models.Appointment.department_id == branch.id,
                models.Appointment.time_slot >= today_start,
                models.Appointment.time_slot < today_end
            ).scalar() or 0

            branch_data.append([
                str(branch.id),
                Paragraph(branch.name, styles['CustomNormal']), # Wrap long names
                "СпецЦОН" if branch.is_special else "Обычный ЦОН",
                Paragraph(branch.address, styles['CustomNormal']), # Wrap long addresses
                str(total_appts),
                str(today_appts)
            ])

        # Create branch table with adjusted column widths
        branch_table = Table(branch_data, colWidths=[30, 140, 80, 150, 50, 50]) # Adjust widths as needed
        branch_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), # Vertical align
            ('FONTNAME', (0, 0), (-1, 0), 'ArialUnicodeMS'),
            ('FONTSIZE', (0, 0), (-1, 0), 12), # Smaller header
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'ArialUnicodeMS'), # Ensure font for data too
            ('FONTSIZE', (0, 1), (-1, -1), 10), # Smaller data font
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            # Alignment for specific columns if needed
            ('ALIGN', (1, 1), (1, -1), 'LEFT'), # Align names left
            ('ALIGN', (3, 1), (3, -1), 'LEFT'), # Align addresses left
        ]))
        elements.append(branch_table)

    elements.append(Spacer(1, 30))

    # --- Appointments Section ---
    elements.append(Paragraph('Записи', styles['CustomHeading1']))
    elements.append(Spacer(1, 12))

    appointments = db.query(models.Appointment).join(models.Department).order_by(models.Appointment.id.asc()).all()
    if appointments:
        # Header row for appointments - Added IIN and Service
        appointment_data = [['ID', 'Отделение', 'Дата и время', 'ИИН', 'Имя', 'Телефон', 'Услуга']]

        for appt in appointments:
            appointment_data.append([
                str(appt.id),
                Paragraph(appt.department.name, styles['CustomNormal']), # Wrap
                appt.time_slot.strftime("%Y-%m-%d %H:%M"),
                appt.iin, # Added IIN
                Paragraph(appt.user_name or "Н/Д", styles['CustomNormal']), # Wrap
                appt.phone_number or "Н/Д",
                Paragraph(appt.service, styles['CustomNormal']) # Added Service, wrap
            ])

        # Create the appointments table with adjusted column widths
        appt_table = Table(appointment_data, colWidths=[30, 100, 100, 90, 80, 80, 100]) # Adjust widths
        appt_table.setStyle(TableStyle([
           ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), # Vertical align
            ('FONTNAME', (0, 0), (-1, 0), 'ArialUnicodeMS'),
            ('FONTSIZE', (0, 0), (-1, 0), 11), # Smaller header
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'ArialUnicodeMS'), # Ensure font for data
            ('FONTSIZE', (0, 1), (-1, -1), 9), # Smaller data font
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
             # Alignment for specific columns
            ('ALIGN', (1, 1), (1, -1), 'LEFT'), # Dept Name
            ('ALIGN', (4, 1), (4, -1), 'LEFT'), # User Name
            ('ALIGN', (6, 1), (6, -1), 'LEFT'), # Service
        ]))
        elements.append(appt_table)

    # Build PDF document
    doc.build(elements)
    buffer.seek(0)

    # Return the PDF
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=tson_report_{current_time.strftime('%Y%m%d_%H%M%S')}.pdf"
        }
    )