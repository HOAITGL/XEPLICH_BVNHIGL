from models import db
from datetime import datetime

class Timesheet2(db.Model):
    __tablename__ = 'timesheet2'
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    name = db.Column(db.String(255), default='Bảng chấm công BHYT')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    entries = db.relationship('Timesheet2Entry', backref='sheet', cascade="all, delete-orphan")

class Timesheet2Entry(db.Model):
    __tablename__ = 'timesheet2_entry'
    id = db.Column(db.Integer, primary_key=True)
    sheet_id = db.Column(db.Integer, db.ForeignKey('timesheet2.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    code = db.Column(db.String(50), default='')  # ký hiệu/ca: "Sáng/Chiều" hoặc "XĐ"…
    deleted = db.Column(db.Boolean, default=False)

    user = db.relationship('User')
