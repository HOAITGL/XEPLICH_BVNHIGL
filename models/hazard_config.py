
from extensions import db

class HazardConfig(db.Model):
    __tablename__ = 'hazard_config'
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(100), nullable=False)
    hazard_level = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(10), nullable=False)
    duration_hours = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)


