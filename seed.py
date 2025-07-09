import os
from extensions import db
from models.user import User
from models.shift import Shift
from models.shift_rate_config import ShiftRateConfig
from flask import Flask
from models.leave_request import LeaveRequest

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')  # fallback nếu thiếu env
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()  # ✅ chỉ tạo nếu chưa có bảng

    # 👤 Chỉ thêm admin nếu chưa tồn tại
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
        db.session.add(ShiftRateConfig(**rate))

    # 🏥 Cấu hình khoa
    from models.department_setting import DepartmentSetting
    if not DepartmentSetting.query.filter_by(department_name="Khoa xét nghiệm").first():
        db.session.add(DepartmentSetting(department_name="Khoa xét nghiệm", max_people_per_day=2))
        
    db.session.commit()
    print("✅ Dữ liệu mẫu đã được khởi tạo.")
