# init_db.py
from flask import Flask
from models import db
from models.user import User
from models.permission import Permission

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def init_database():
    with app.app_context():
        print("🔄 Đang tạo lại toàn bộ cơ sở dữ liệu...")
        db.drop_all()
        db.create_all()

        print("👤 Tạo người dùng mẫu...")
        admin = User(
            name="Quản trị viên",
            username="admin",
            password="admin",
            role="admin",
            department="Phòng CNTT",
            position="Bác sĩ"
        )
        manager = User(
            name="Nguyễn Văn A",
            username="nva",
            password="123",
            role="manager",
            department="Khoa Nội",
            position="Điều dưỡng"
        )
        user = User(
            name="Trần Thị B",
            username="ttb",
            password="123",
            role="user",
            department="Khoa Ngoại",
            position="Kỹ thuật viên"
        )
        db.session.add_all([admin, manager, user])
        db.session.flush()

        modules = [
            'trang_chu', 'xem_lich_truc', 'yeu_cau_cv_ngoai_gio', 'don_nghi_phep',
            'xep_lich_truc', 'tong_hop_khth', 'cham_cong', 'bang_cong_gop', 'bang_tinh_tien_truc',
            'cau_hinh_ca_truc', 'thiet_lap_phong_kham', 'nhan_su_theo_khoa',
            'cau_hinh_tien_truc', 'thiet_lap_khoa_hscc', 'phan_quyen',
            'danh_sach_cong_viec', 'xem_log', 'doi_mat_khau'
        ]

        def create_permissions_for(user, allowed_modules):
            return [Permission(user_id=user.id, module_name=m, can_access=(m in allowed_modules)) for m in modules]

        admin_perms = create_permissions_for(admin, modules)
        manager_perms = create_permissions_for(manager, ['trang_chu', 'xem_lich_truc', 'xep_lich_truc', 'don_nghi_phep'])
        user_perms = create_permissions_for(user, ['trang_chu', 'xem_lich_truc'])

        db.session.add_all(admin_perms + manager_perms + user_perms)
        db.session.commit()
        print("✅ Dữ liệu mẫu và phân quyền đã được thiết lập.")

if __name__ == "__main__":
    init_database()
