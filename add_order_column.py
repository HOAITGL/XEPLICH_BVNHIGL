from models import db
from models.shift import Shift
from models import db
from sqlalchemy.exc import OperationalError

with app.app_context():
    try:
        # Thêm cột 'order' nếu chưa có
        db.session.execute('ALTER TABLE shift ADD COLUMN "order" INTEGER DEFAULT 0;')
        db.session.commit()
        print("Đã thêm cột 'order'.")
    except OperationalError:
        print("Cột 'order' đã tồn tại, bỏ qua bước thêm cột.")

    # Cập nhật giá trị mặc định dựa trên id
    shifts = Shift.query.order_by(Shift.id).all()
    for i, s in enumerate(shifts):
        s.order = i
    db.session.commit()

    print("Đã cập nhật giá trị mặc định cho cột 'order'.")
