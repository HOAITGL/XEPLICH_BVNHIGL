from extensions import db
from models.user import User

class Ca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(50))  # VD: Ca A, Ca B

    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    nurse1_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    nurse2_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    doctor = db.relationship('User', foreign_keys=[doctor_id])
    nurse1 = db.relationship('User', foreign_keys=[nurse1_id])
    nurse2 = db.relationship('User', foreign_keys=[nurse2_id])

    def __repr__(self):
        return f"<Ca {self.name} - {self.department}>"




