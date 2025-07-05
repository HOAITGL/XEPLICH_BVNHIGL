
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from extensions import db

class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20))  # admin / manager / user
    department = db.Column(db.String(100))
    position = db.Column(db.String(50))  # Bác sĩ / Điều dưỡng / KTV...
    contract_type = db.Column(db.String(50))  # Hợp đồng / Biên chế / v.v.
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    start_year = db.Column(db.Integer)  # ✅ Năm vào công tác (mới thêm)

    # Quan hệ đến lịch trực
    schedules = relationship("Schedule", back_populates="user")
    leave_requests = relationship('LeaveRequest', back_populates='user')

