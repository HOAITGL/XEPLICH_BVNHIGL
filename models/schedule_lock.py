
from datetime import datetime
from extensions import db
from models.user import User

class ScheduleLock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    locked_at = db.Column(db.DateTime, default=datetime.utcnow)
    locked_by = db.Column(db.Integer, db.ForeignKey('user.id'))

