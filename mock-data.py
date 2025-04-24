from database import SessionLocal, engine, Base
from models import Department, Appointment
from faker import Faker
from datetime import datetime, timedelta, time
import random
import datetime_utils
from config import settings

# Initialize Faker
fake = Faker()

# Service lists (copied from crud.py for simplicity)
REGULAR_TSON_SERVICES = [
    "Консультация", "Услуги НПЦЗем", "Нәтиже",
    "Социальные услуги", "Льготные категории", "Выдача документов",
]
SPECIAL_TSON_SERVICES = [
    "Механика B", "Категории D,E,A,D1", "Категория C1", "Категория C",
    "B автомат", "Осмотр ТС", "Регистрация (перерегистрация) ТС",
    "СРТС и доверенности", "Водительское удостоверение",
    "Льготное окно ВУ", "Выдача СРТС",
]

# Working hours from config
WORKING_START_HOUR = settings.WORKING_HOURS["start"]
WORKING_END_HOUR = settings.WORKING_HOURS["end"]

# Create tables
print("Dropping and Creating tables...")
Base.metadata.drop_all(bind=engine) # Optional: Drop existing tables for a clean slate
Base.metadata.create_all(bind=engine)
print("Tables created.")

# Create database session
db = SessionLocal()

# Create real ЦОН departments from Astana
# Designate one as a "СпецЦОН" for demonstration
departments_data = [
    {
        "name": "СпецЦОН №1 (Сарыарка)", # Marked as special
        "address": "г. Астана, район Сарыарка, ул. №20-40, здание 2",
        "is_special": True
    },
    {
        "name": "ЦОН района Алматы",
        "address": "г. Астана, район Алматы, ул. К. Сатпаева, 25",
        "is_special": False
    },
    {
        "name": "ЦОН района Есиль",
        "address": "г. Астана, район Есиль, ул. Мангилик Ел, 30",
        "is_special": False
    },
    {
        "name": "ЦОН района Байконур",
        "address": "г. Астана, район Байконур, ул. Иманова, 20/1",
        "is_special": False
    },
     {
        "name": "ЦОН района Нура",
        "address": "г. Астана, район Нура, проспект Кабанбай батыра, 6/3",
        "is_special": False
    }
]

print("Adding departments...")
# Add departments to database
departments_map = {} # Store department objects for easy access
for dept_data in departments_data:
    department = Department(**dept_data)
    db.add(department)
    db.flush() # Flush to get the ID
    departments_map[department.id] = department # Store the object

db.commit()
print(f"{len(departments_map)} departments added.")

# Generate appointments for the next 7 days
today = datetime.now().date()
start_date = today
end_date = start_date + timedelta(days=7)

# Get all department IDs
department_ids = list(departments_map.keys())

print(f"Generating appointments from {start_date} to {end_date}...")
appointment_count = 0
# Iterate through each day
current_day = start_date
while current_day <= end_date:
    # Iterate through each hour slot within working hours for the current day
    for hour in range(WORKING_START_HOUR, WORKING_END_HOUR):
        # Create two slots per hour: one at XX:00 and one at XX:30
        for minute in [0, 30]:
            # Create naive datetime for the slot - no timezone handling
            slot_time = datetime.combine(current_day, time(hour, minute))

            # For each department, potentially create an appointment
            for dept_id in department_ids:
                # Check if this time slot is already taken for this department
                existing = db.query(Appointment).filter(
                    Appointment.department_id == dept_id,
                    Appointment.time_slot == slot_time
                ).first()

                if not existing and random.random() < 0.3:  # 30% chance to create an appointment
                    # Generate Kazakhstan phone number format (7XXXXXXXXXX)
                    phone_number = f"77{random.randint(10000000, 99999999)}" # More realistic format

                    # Generate 12-digit IIN
                    iin = "".join([str(random.randint(0, 9)) for _ in range(12)])

                    # Get the department object
                    department = departments_map[dept_id]

                    # Choose service based on department type
                    if department.is_special:
                        service = random.choice(SPECIAL_TSON_SERVICES)
                    else:
                        service = random.choice(REGULAR_TSON_SERVICES)

                    appointment = Appointment(
                        department_id=dept_id,
                        time_slot=slot_time, # Store naive datetime
                        user_name=fake.name(),
                        phone_number=phone_number,
                        iin=iin,
                        service=service
                    )
                    db.add(appointment)
                    appointment_count += 1

    current_day += timedelta(days=1) # Move to the next day

print(f"Committing {appointment_count} appointments...")
db.commit()
db.close()

print("Mock data has been generated successfully!")