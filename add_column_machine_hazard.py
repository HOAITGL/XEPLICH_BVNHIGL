from sqlalchemy import inspect, text
from extensions import db
from app import app

with app.app_context():
    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('hazard_config')]

    if 'machine_type' not in columns:
        print("Đang thêm cột machine_type vào hazard_config...")
        db.session.execute(text('ALTER TABLE hazard_config ADD COLUMN machine_type TEXT'))
        db.session.commit()
        print("✅ Đã thêm cột machine_type thành công.")
    else:
        print("⚠ Cột machine_type đã tồn tại, không cần thêm lại.")
