
from extensions import db

class CaConfiguration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(100), nullable=False)

    num_shifts = db.Column(db.Integer, default=3)        # Số ca/ngày
    cas_per_shift = db.Column(db.Integer, default=2)     # Số ca/ca làm
    doctors_per_ca = db.Column(db.Integer, default=1)    # Bác sĩ/ca
    nurses_per_ca = db.Column(db.Integer, default=2)     # Điều dưỡng/ca

    def __repr__(self):
        return f"<Ca_Config {self.department}: {self.num_shifts} ca/ngày>"
