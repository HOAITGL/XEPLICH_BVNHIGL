from models import db
from models.user import User

with app.app_context():
    # Đổi tên khoa tại đây nếu cần
    khoa_can_kiem_tra = 'Khoa XYZ'

    users = User.query.filter_by(department=khoa_can_kiem_tra).all()

    if users:
        print(f"Danh sách nhân sự trong '{khoa_can_kiem_tra}':")
        for u in users:
            print(f"- {u.name} | {u.username} | {u.role}")
    else:
        print(f"❌ Không tìm thấy nhân sự nào thuộc khoa '{khoa_can_kiem_tra}'")

