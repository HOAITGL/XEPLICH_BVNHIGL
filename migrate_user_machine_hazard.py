from extensions import db
from flask import Flask
from models.user_machine_hazard import UserMachineHazard
import os

app = Flask(__name__)
db_url = os.getenv("DATABASE_URL") or "sqlite:///database.db"
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    # Tạo bảng nếu chưa có
    if not db.engine.dialect.has_table(db.engine.connect(), 'user_machine_hazard'):
        db.create_all()
        print("✅ Tạo bảng user_machine_hazard thành công")
    else:
        print("⚠ Bảng user_machine_hazard đã tồn tại")
