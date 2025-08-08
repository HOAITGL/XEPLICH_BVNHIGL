from extensions import db

class UserMachineHazard(db.Model):
    __tablename__ = 'user_machine_hazard'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    machine_type = db.Column(db.String(100), nullable=False, default='Tất cả máy')
    start_date = db.Column(db.Date, nullable=True)   # Cho phép NULL
    end_date = db.Column(db.Date, nullable=True)     # Cho phép NULL

    user = db.relationship("User", backref="machine_hazards")
