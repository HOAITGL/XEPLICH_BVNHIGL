from extensions import db

class ShiftRateConfig(db.Model):
    __tablename__ = 'shift_rate_config'

    id = db.Column(db.Integer, primary_key=True)
    ca_loai = db.Column(db.String(10), nullable=False)         # "16h" hoặc "24h"
    truc_loai = db.Column(db.String(10), nullable=False)       # "thường" hoặc "HSCC"
    ngay_loai = db.Column(db.String(20), nullable=False)       # "ngày_thường", "ngày_nghỉ", "ngày_lễ"
    don_gia = db.Column(db.Integer, nullable=False)            # Ví dụ: 117000
