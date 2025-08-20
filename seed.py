# seed.py
from datetime import date, timedelta, time
from extensions import db
from models import db
from models.user import User
from models.shift import Shift
from models.schedule import Schedule
from models.hazard_config import HazardConfig

with app.app_context():
    db.drop_all()
    db.create_all()

    # ===== 1. Seed Users =====
    users = [
        User(name="Nguyễn Thị Lệ Xuân", position="TK", department="Khoa Xét Nghiệm - GPB", active=True),
        User(name="Vũ Thị Kim Thu", position="PTK", department="Khoa Xét Nghiệm - GPB", active=True),
        User(name="Hồ Anh Tuấn", position="PTK", department="Khoa Hồi sức - TCCĐ", active=True),
        User(name="Trần Ngọc Đức", position="BS", department="Khoa Hồi sức - TCCĐ", active=True),
    ]
    db.session.add_all(users)
    db.session.commit()

    # ===== 2. Seed Shifts =====
    shifts = [
        Shift(name="Ca sáng", code="S", start_time=time(7, 0), end_time=time(15, 0), duration=8, order=1),
        Shift(name="Ca chiều", code="C", start_time=time(15, 0), end_time=time(23, 0), duration=8, order=2),
        Shift(name="Ca đêm", code="D", start_time=time(23, 0), end_time=time(7, 0), duration=8, order=3),
    ]
    db.session.add_all(shifts)
    db.session.commit()

    # ===== 3. Seed HazardConfig =====
    hazard_configs = [
        # Khoa Xét nghiệm – máy Huyết học
        HazardConfig(department="Khoa Xét Nghiệm - GPB", position="TK",
                     machine_type="Huyết học", duration_hours=8, hazard_level=0.3,
                     start_date=date(2025, 8, 1), end_date=date(2025, 8, 31)),
        HazardConfig(department="Khoa Xét Nghiệm - GPB", position="PTK",
                     machine_type="Sinh hóa", duration_hours=8, hazard_level=0.3,
                     start_date=date(2025, 8, 1), end_date=date(2025, 8, 31)),

        # Khoa Hồi sức – không theo máy
        HazardConfig(department="Khoa Hồi sức - TCCĐ", position="PTK",
                     duration_hours=8, hazard_level=0.2,
                     start_date=date(2025, 8, 1), end_date=date(2025, 8, 31)),
        HazardConfig(department="Khoa Hồi sức - TCCĐ", position="BS",
                     duration_hours=8, hazard_level=0.2,
                     start_date=date(2025, 8, 1), end_date=date(2025, 8, 31)),
    ]
    db.session.add_all(hazard_configs)
    db.session.commit()

    # ===== 4. Seed Schedule =====
    today = date(2025, 8, 1)
    end_date = date(2025, 8, 25)
    day_count = (end_date - today).days + 1

    schedules = []
    for i in range(day_count):
        work_day = today + timedelta(days=i)

        # Khoa Xét nghiệm – 2 user, 2 máy khác nhau
        schedules.append(Schedule(user_id=users[0].id, shift_id=shifts[0].id,
                                   work_date=work_day, machine_type="Huyết học", work_hours=8))
        schedules.append(Schedule(user_id=users[1].id, shift_id=shifts[0].id,
                                   work_date=work_day, machine_type="Sinh hóa", work_hours=8))

        # Khoa Hồi sức – 2 user, không máy
        schedules.append(Schedule(user_id=users[2].id, shift_id=shifts[1].id,
                                   work_date=work_day, work_hours=8))
        schedules.append(Schedule(user_id=users[3].id, shift_id=shifts[1].id,
                                   work_date=work_day, work_hours=8))

    db.session.add_all(schedules)
    db.session.commit()

    print("✅ Seed dữ liệu hoàn tất.")
