from extensions import db
from datetime import date

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='leaves')  # dòng này là quan trọng!

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(200))
    location = db.Column(db.String(100))  # nếu có
    birth_date = db.Column(db.Date)       # nếu có
    department = db.Column(db.String)
