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
    db.drop_all()
    db.create_all()

    # 👤 Thêm người dùng mẫu đầy đủ thông tin
    admin = User(
        name="Quản trị viên",
        username="admin",
        password="admin",
        role="admin",
        department="Phòng CNTT",
        position="Bác sĩ",
        start_year=2010
    )
    user1 = User(
        name="Nguyễn Văn A",
        username="nva",
        password="123",
        role="manager",
        department="Khoa Nội",  # cần trùng với các lịch trực để nút ký hoạt động
        position="Điều dưỡng",
        start_year=2015
    )
    user2 = User(
        name="Trần Thị B",
        username="ttb",
        password="123",
        role="user",
        department="Khoa Ngoại",
        position="Kỹ thuật viên",
        start_year=2018
    )
    db.session.add_all([admin, user1, user2])

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

    db.session.commit()
    print("✅ Dữ liệu mẫu đã được khởi tạo.")
