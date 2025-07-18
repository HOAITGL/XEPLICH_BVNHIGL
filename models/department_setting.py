# models/department_setting.py
from extensions import db

class DepartmentSetting(db.Model):
    __tablename__ = 'department_setting'
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(100), nullable=False, unique=True)
    key = db.Column(db.String(100), nullable=True)
    value = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<DepartmentSetting {self.department} - {self.key}>'


