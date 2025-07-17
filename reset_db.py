from app import app, db

if __name__ == "__main__":
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("✅ Đã xóa và tạo lại toàn bộ cơ sở dữ liệu.")
