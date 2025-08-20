from sqlalchemy import inspect, text
from extensions import db
from models import db


with app.app_context():
    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('schedule')]

    # Thêm cột machine_type
    if 'machine_type' not in columns:
        engine_name = db.engine.url.get_backend_name()
        if engine_name == "postgresql":
            db.session.execute(text('ALTER TABLE schedule ADD COLUMN machine_type TEXT'))
            print("✅ Đã thêm cột machine_type (PostgreSQL).")
        else:
            # SQLite không hỗ trợ ALTER ADD COLUMN kiểu chuẩn
            db.session.execute(text('ALTER TABLE schedule ADD COLUMN machine_type TEXT'))
            print("✅ Đã thêm cột machine_type (SQLite).")

    # Thêm cột work_hours
    if 'work_hours' not in columns:
        engine_name = db.engine.url.get_backend_name()
        if engine_name == "postgresql":
            db.session.execute(text('ALTER TABLE schedule ADD COLUMN work_hours FLOAT'))
            print("✅ Đã thêm cột work_hours (PostgreSQL).")
        else:
            db.session.execute(text('ALTER TABLE schedule ADD COLUMN work_hours FLOAT'))
            print("✅ Đã thêm cột work_hours (SQLite).")

    db.session.commit()
    print("🎉 Hoàn tất thêm cột mới cho bảng Schedule.")
