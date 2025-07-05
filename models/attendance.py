from extensions import db
from datetime import date

class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=False)
    department = db.Column(db.String(100))
    status = db.Column(db.String(50))  # ví dụ: "Công", "Nghỉ", "Phép", v.v.

    user = db.relationship('User', backref='attendances')
    shift = db.relationship('Shift', backref='attendances')

    def __repr__(self):
        return f'<Attendance {self.user_id} {self.date} Shift:{self.shift_id}>'
