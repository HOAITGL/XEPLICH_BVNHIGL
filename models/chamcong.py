from models import db
from datetime import date

class ChamCong(db.Model):
    __tablename__ = 'cham_cong'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    shift_code = db.Column(db.String(50), nullable=False)

    # Liên kết với bảng người dùng nếu cần
    user = db.relationship('User', backref='cham_congs')
