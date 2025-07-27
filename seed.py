import os
from extensions import db
from models.user import User
from models.shift_rate_config import ShiftRateConfig
from models.department_setting import DepartmentSetting
from sqlalchemy import inspect, text
from flask import Flask

app = Flask(__name__)

# Cấu hình kết nối DB (fallback SQLite nếu local không có PostgreSQL)
db_url = os.getenv("DATABASE_URL") or "sqlite:///database.db"
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    # KHÔNG dùng create_all() để tránh mất dữ liệu – chỉ chạy upgrade migration

    # 1. Seed admin user
    if not User.query.filter_by(username='admin').first():
        admin = User(
            name="Quản trị viên",
            username="admin",
            password="admin",
            role="admin",
            department="Phòng CNTT",
            position="Bác sĩ",
            start_year=2010
        )
        db.session.add(admin)
        print("✅ Đã thêm tài khoản admin mặc định.")

    # 2. Seed bảng đơn giá trực
    rates = [
        {"ca_loai": "16h", "truc_loai": "thường", "ngay_loai": "ngày_thường", "don_gia": 67500},
        {"ca_loai": "16h", "truc_loai": "thường", "ngay_loai": "ngày_nghỉ", "don_gia": 117000},
        {"ca_loai": "16h", "truc_loai": "thường", "ngay_loai": "ngày_lễ", "don_gia": 162000},
        {"ca_loai": "16h", "truc_loai": "HSCC", "ngay_loai": "ngày_thường", "don_gia": 101250},
        {"ca_loai": "16h", "truc_loai": "HSCC", "ngay_loai": "ngày_nghỉ", "don_gia": 175500},
        {"ca_loai": "16h", "truc_loai": "HSCC", "ngay_loai": "ngày_lễ", "don_gia": 243000},
        {"ca_loai": "24h", "truc_loai": "thường", "ngay_loai": "ngày_thường", "don_gia": 90000},
        {"ca_loai": "24h", "truc_loai": "thường", "ngay_loai": "ngày_nghỉ", "don_gia": 117000},
        {"ca_loai": "24h", "truc_loai": "thường", "ngay_loai": "ngày_lễ", "don_gia": 162000},
        {"ca_loai": "24h", "truc_loai": "HSCC", "ngay_loai": "ngày_thường", "don_gia": 101250},
        {"ca_loai": "24h", "truc_loai": "HSCC", "ngay_loai": "ngày_nghỉ", "don_gia": 175500},
        {"ca_loai": "24h", "truc_loai": "HSCC", "ngay_loai": "ngày_lễ", "don_gia": 243000},
    ]
    for rate in rates:
        if not ShiftRateConfig.query.filter_by(**rate).first():
            db.session.add(ShiftRateConfig(**rate))

    # 3. Seed cấu hình khoa
    if not DepartmentSetting.query.filter_by(department="Khoa xét nghiệm", key="max_people_per_day").first():
        db.session.add(DepartmentSetting(department="Khoa xét nghiệm", key="max_people_per_day", value="2"))

    # 4. Thêm cột 'active' vào bảng user nếu chưa có (PostgreSQL)
    inspector = inspect(db.engine)
    user_columns = [col['name'] for col in inspector.get_columns('user')]
    if 'active' not in user_columns:
        engine_name = db.engine.url.get_backend_name()
        if engine_name == "postgresql":
            try:
                db.session.execute(text('ALTER TABLE "user" ADD COLUMN active BOOLEAN DEFAULT TRUE'))
                print("✅ Đã thêm cột 'active' vào bảng user.")
            except Exception as e:
                print(f"⚠ Không thể thêm cột 'active': {e}")
        else:
            print("⚠ SQLite: Bỏ qua thêm cột 'active' (cần migrate thủ công)")

    db.session.commit()
    print("✅ Seed dữ liệu mẫu hoàn tất.")
