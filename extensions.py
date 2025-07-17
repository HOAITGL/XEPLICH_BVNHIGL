from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()  # ✅ Chỉ tạo 1 lần ở đây
from flask_migrate import Migrate
migrate = Migrate()
