from sqlalchemy import inspect, text
from extensions import db
from app import app

with app.app_context():
    inspector = inspect(db.engine)
    engine_name = db.engine.url.get_backend_name()
    changed = False

    # ====== Bảng schedule ======
    schedule_cols = [c['name'] for c in inspector.get_columns('schedule')]

    if 'machine_type' not in schedule_cols:
        db.session.execute(text('ALTER TABLE schedule ADD COLUMN machine_type TEXT'))
        print(f"✅ Đã thêm cột machine_type cho schedule ({engine_name}).")
        changed = True

    if 'work_hours' not in schedule_cols:
        db.session.execute(text('ALTER TABLE schedule ADD COLUMN work_hours FLOAT'))
        print(f"✅ Đã thêm cột work_hours cho schedule ({engine_name}).")
        changed = True

    # ====== Bảng hazard_config ======
    hazard_cols = [c['name'] for c in inspector.get_columns('hazard_config')]

    if 'machine_type' not in hazard_cols:
        db.session.execute(text('ALTER TABLE hazard_config ADD COLUMN machine_type TEXT'))
        print(f"✅ Đã thêm cột machine_type cho hazard_config ({engine_name}).")
        changed = True

    # ====== Commit nếu có thay đổi ======
    if changed:
        db.session.commit()
        print("🎉 Hoàn tất thêm cột mới cho các bảng.")
    else:
        print("⚠ Không có thay đổi, tất cả cột đã tồn tại.")
