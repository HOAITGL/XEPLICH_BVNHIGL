import smtplib
from email.message import EmailMessage
import os

def send_schedule_email(user, pdf_path):
    if not user.email:
        return "Không có email để gửi."

    msg = EmailMessage()
    msg['Subject'] = 'Lịch trực của bạn'
    msg['From'] = 'your_email@gmail.com'  # 🔁 Thay bằng email của bạn
    msg['To'] = user.email
    msg.set_content(f"Chào {user.name},\n\nĐây là lịch trực của bạn.\n\nTrân trọng.")

    # Đính kèm file PDF
    with open(pdf_path, 'rb') as f:
        file_data = f.read()
        file_name = os.path.basename(pdf_path)
        msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=file_name)

    # Gửi qua Gmail SMTP (cần bật mật khẩu ứng dụng)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login('your_email@gmail.com', 'your_app_password')  # 🔁 Dùng mật khẩu ứng dụng
        smtp.send_message(msg)

@app.route('/send-email/<int:user_id>')
def send_email(user_id):
    user = User.query.get(user_id)

    # Giả sử bạn có hàm generate_schedule_pdf trả về đường dẫn file PDF
    pdf_path = generate_schedule_pdf(user.id)  # cần định nghĩa hàm này

    send_schedule_email(user, pdf_path)
    return redirect('/users-by-department')
