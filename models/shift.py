from sqlalchemy import Column, Integer, String, Time, Float
from extensions import db

class Shift(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    duration = Column(Float, nullable=False)
    order = Column(Integer, default=0)  # ➕ Cột sắp xếp

    def __repr__(self):
        return f"<Shift {self.name} ({self.code})>"


