
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from extensions import db

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20))  # admin / manager / user
    department = db.Column(db.String(100))
    position = db.Column(db.String(50))  # Bác sĩ / Điều dưỡng / KTV...
    contract_type = db.Column(db.String(50))  # ✅ thêm dòng này
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))


    schedules = relationship("Schedule", back_populates="user")

