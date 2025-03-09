from database import SessionLocal, engine, Base
from models import Department, Appointment
from faker import Faker
from datetime import datetime, timedelta
import random

# Initialize Faker
fake = Faker()

# Create tables
Base.metadata.create_all(bind=engine)

# Create database session
db = SessionLocal()

# Create sample departments
departments = [
    {"name": "Cardiology Department", "address": fake.address()},
    {"name": "Orthopedics Department", "address": fake.address()},
    {"name": "Pediatrics Department", "address": fake.address()},
    {"name": "Neurology Department", "address": fake.address()},
    {"name": "Dental Department", "address": fake.address()}
]

# Add departments to database
for dept_data in departments:
    department = Department(**dept_data)
    db.add(department)

db.commit()

# Generate appointments for the next 7 days
start_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
end_date = start_date + timedelta(days=7)

# Get all department IDs
department_ids = [dept.id for dept in db.query(Department).all()]

# Generate appointments
current_date = start_date
while current_date < end_date:
    if current_date.hour >= 9 and current_date.hour < 18:
        # For each hour, create appointments
        for dept_id in department_ids:
            # Check if this time slot is already taken for this department
            existing = db.query(Appointment).filter(
                Appointment.department_id == dept_id,
                Appointment.time_slot == current_date
            ).first()
            
            if not existing and random.random() < 0.3:  # 30% chance to create an appointment
                appointment = Appointment(
                    department_id=dept_id,
                    time_slot=current_date,
                    user_name=fake.name(),
                    phone_number=fake.phone_number()
                )
                db.add(appointment)
    
    current_date += timedelta(hours=1)

db.commit()
db.close()

print("Mock data has been generated successfully!")