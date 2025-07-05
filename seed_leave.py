from models.leave_request import LeaveRequest
from models.user import User
from datetime import date

with app.app_context():
    user = User.query.first()  # Giả sử đã có ít nhất 1 nhân viên

    if user:
        leave = LeaveRequest(
            user_id=user.id,
            start_date=date(2025, 6, 30),
            end_date=date(2025, 7, 6),
            reason="Về quê thăm cha mẹ",
            location="Xã Phước Hiệp, Huyện Tuy Phước, Bình Định",
            birth_date=date(1982, 7, 21)
        )

        db.session.add(leave)
        db.session.commit()

        print("✅ Tạo thành công đơn nghỉ phép với ID:", leave.id)
    else:
        print("❌ Không có nhân viên nào trong hệ thống.")
