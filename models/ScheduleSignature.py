
from datetime import datetime
from extensions import db

class ScheduleSignature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(100), nullable=False)
    from_date = db.Column(db.Date, nullable=False)
    to_date = db.Column(db.Date, nullable=False)
    signed_by = db.Column(db.String(100), nullable=False)
    signed_at = db.Column(db.DateTime, default=datetime.utcnow)



