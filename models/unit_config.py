from extensions import db

class UnitConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))         # Tên đơn vị
    address = db.Column(db.String(200))      # Địa chỉ liên hệ
    phone = db.Column(db.String(100))        # Số điện thoại
