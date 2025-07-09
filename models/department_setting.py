from extensions import db

class DepartmentSetting(db.Model):
    __tablename__ = 'department_setting'

    id = db.Column(db.Integer, primary_key=True)
    department_name = db.Column(db.String(255), nullable=False, unique=True)
    max_people_per_day = db.Column(db.Integer, nullable=False, default=1)


