import os
from extensions import db
from models.user import User
from models.shift import Shift
from models.shift_rate_config import ShiftRateConfig
from flask import Flask
from models.leave_request import LeaveRequest
from models.department_setting import DepartmentSetting
from sqlalchemy import inspect, text

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL") or 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

    # 👤 Thêm admin nếu chưa có
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

    # 💰 Thêm đơn giá trực
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

    # 🏥 Cấu hình khoa
    if not DepartmentSetting.query.filter_by(department="Khoa xét nghiệm", key="max_people_per_day").first():
        db.session.add(DepartmentSetting(department="Khoa xét nghiệm", key="max_people_per_day", value="2"))

    # ✅ Kiểm tra cột 'active' trong bảng user, nếu chưa có thì thêm
    inspector = inspect(db.engine)
    user_columns = [col['name'] for col in inspector.get_columns('user')]
    if 'active' not in user_columns:
        try:
            db.session.execute(text("ALTER TABLE user ADD COLUMN active BOOLEAN DEFAULT 1"))
            print("✅ Đã thêm cột 'active' vào bảng user.")
        except Exception as e:
            print(f"❌ Lỗi khi thêm cột 'active': {e}")

    db.session.commit()
    print("✅ Dữ liệu mẫu đã được khởi tạo.")
