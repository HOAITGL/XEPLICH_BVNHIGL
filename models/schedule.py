from extensions import db
from sqlalchemy.orm import relationship
from datetime import date

class Schedule(db.Model):
    __tablename__ = 'schedule'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'))
    work_date = db.Column(db.Date)

    # Thêm 2 cột mới để hỗ trợ tính độc hại
    machine_type = db.Column(db.String(50), nullable=True)  # Ví dụ: Máy huyết học, Máy vi sinh
    work_hours = db.Column(db.Float, nullable=True)         # Số giờ làm trong ca

    user = relationship("User", back_populates="schedules")
    shift = relationship("Shift")
