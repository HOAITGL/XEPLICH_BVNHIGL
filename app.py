from models.schedule_lock import ScheduleLock

from functools import wraps

def session_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade
from models import ScheduleSignature
from models.ScheduleSignature import ScheduleSignature
from extensions import db  # Sử dụng đối tượng db đã khởi tạo trong extensions.py
from openpyxl import Workbook
from io import BytesIO
from logging.handlers import RotatingFileHandler
from flask_migrate import Migrate
from models.permission import Permission
from models.unit_config import UnitConfig
from models.user import User

from logging.handlers import RotatingFileHandler
import logging, os

def setup_logging(app):
    if not os.path.exists('logs'):
        os.mkdir('logs')
    log_handler = RotatingFileHandler('logs/activity.log', maxBytes=1000000, backupCount=5)
    log_handler.setLevel(logging.INFO)
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    log_handler.setFormatter(log_formatter)
    
    # Tránh thêm nhiều handler nếu đã có
    if not any(isinstance(h, RotatingFileHandler) for h in app.logger.handlers):
        app.logger.addHandler(log_handler)
    
    app.logger.setLevel(logging.INFO)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL") or 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'lichtruc2025'

# ✅ Gắn app vào SQLAlchemy
db.init_app(app)

# ✅ Tạo bảng nếu thiếu (dùng cho Render khi không gọi __main__)
with app.app_context():
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()
    required_tables = {'user', 'permission'}

    if not required_tables.issubset(set(existing_tables)):
        db.create_all()
        print("✅ Đã tạo bảng user/permission trên Render.")
    else:
        print("✅ Các bảng chính đã tồn tại.")

setup_logging(app)

migrate = Migrate(app, db)

with app.app_context():
    try:
        upgrade()
        print("✅ Đã tự động chạy flask db upgrade.")
    except Exception as e:
        print(f"❌ Lỗi khi upgrade database: {e}")


# ✅ Định nghĩa admin_required
from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("⚠️ Bạn cần đăng nhập.", "danger")
            return redirect(url_for('login'))
        if current_user.role != 'admin':
            flash("❌ Chức năng này chỉ dành cho quản trị viên.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
    allowed_routes = ['login']
    if 'user_id' not in session and request.endpoint not in allowed_routes:
        return redirect('/login')

from flask_login import LoginManager

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Import models
from models.user import User
from models.shift import Shift
from models.schedule import Schedule
from models.ca_config import CaConfiguration
from models.clinic_room import ClinicRoom
from models.ca import Ca

# Import logic
from scheduler.logic import generate_schedule

@app.context_processor
def inject_permissions():
    from models import Permission  # Đảm bảo đã import model Permission
    if 'user_id' in session:
        user_id = session['user_id']
        permissions = Permission.query.filter_by(user_id=user_id, can_access=True).all()

        if permissions:
            allowed_modules = [p.module_name for p in permissions]
        else:
            # Nếu không có phân quyền riêng → fallback theo role
            role = session.get('role')
            default_modules = {
                'admin': [
                    'trang_chu', 'xem_lich_truc', 'xep_lich_truc', 'phan_quyen',
                    'tong_hop_khth', 'cau_hinh_ca_truc', 'cau_hinh_tien_truc',
                    'nhan_su_theo_khoa', 'don_nghi_phep', 'bang_cong_gop',
                    'bang_tinh_tien_truc', 'yeu_cau_cv_ngoai_gio', 'xem_log',
                    'thiet_lap_phong_kham', 'thiet_lap_khoa_hscc', 'cham_cong', 'doi_mat_khau', 'danh_sach_cong_viec'
                ],
                'manager': [
                    'trang_chu', 'xem_lich_truc', 'xep_lich_truc', 'yeu_cau_cv_ngoai_gio',
                    'don_nghi_phep', 'bang_cong_gop', 'nhan_su_theo_khoa', 'doi_mat_khau'
                ],
                'user': [
                    'trang_chu', 'xem_lich_truc', 'don_nghi_phep', 'doi_mat_khau'
                ]
            }
            allowed_modules = default_modules.get(role, [])

        return dict(allowed_modules=allowed_modules)

    return dict(allowed_modules=[])

@app.route('/module-config', methods=['GET', 'POST'])
def edit_module_config():
    if session.get('role') != 'admin':
        return "Bạn không có quyền truy cập chức năng này."

    config_path = os.path.join(os.path.dirname(__file__), 'modules_config.json')

    if request.method == 'POST':
        try:
            data = request.form.get('config_json')
            parsed = json.loads(data)  # kiểm tra JSON hợp lệ
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
            flash("✅ Đã cập nhật cấu hình phân hệ.", "success")
        except Exception as e:
            flash(f"❌ Lỗi khi cập nhật: {str(e)}", "danger")
        return redirect('/module-config')

    with open(config_path, encoding='utf-8') as f:
        current_config = f.read()

    return render_template('edit_module_config.html', config=current_config)

from flask_login import login_user, logout_user
from flask import redirect, url_for, flash
from flask import request, redirect, render_template, flash
from models.user import User

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        app.logger.info(f"[LOGIN] User '{username}' đăng nhập từ IP {request.remote_addr}")

        if not user:
            return "Không tìm thấy tài khoản"

        if user.password != password:
            return f"Mật khẩu không đúng. Đúng là: {user.password}"

        login_user(user)  # ✅ Dòng này là BẮT BUỘC khi dùng Flask-Login
        session['user_id'] = user.id
        session['role'] = user.role
        session['department'] = user.department

        # ✅ Ghi lại log đăng nhập
        app.logger.info(f"[LOGIN] Tài khoản '{username}' đã đăng nhập từ IP {request.remote_addr}")
        
        flash('Đăng nhập thành công!', 'success')
        return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Bạn đã đăng xuất.", "info")
    return redirect(url_for('login'))

@app.route('/leaves')
@login_required
def view_leaves():
    from models.leave_request import LeaveRequest

    user_id = session.get('user_id')
    role = session.get('role')

    if role in ['admin', 'manager']:
        leaves = LeaveRequest.query.order_by(LeaveRequest.start_date.desc()).all()
    else:
        leaves = LeaveRequest.query.filter_by(user_id=user_id).order_by(LeaveRequest.start_date.desc()).all()

    return render_template('leaves.html', leaves=leaves)

from flask_migrate import Migrate
from extensions import db

migrate = Migrate(app, db)

@app.route('/leaves/add', methods=['GET', 'POST'])
@login_required
def add_leave():
    from models.leave_request import LeaveRequest
    from utils.unit_config import get_unit_config

    user_role = session.get('role')
    user_dept = session.get('department')
    current_user_id = session.get('user_id')

    # ✅ Danh sách khoa
    if user_role == 'admin':
        departments = [d[0] for d in db.session.query(User.department)
                       .filter(User.department != None).distinct().all()]
    else:
        departments = [user_dept]

    # ✅ Lấy khoa được chọn
    if request.method == 'POST':
        selected_department = request.form.get('department') if user_role == 'admin' else user_dept
    else:
        selected_department = request.args.get('department') if user_role == 'admin' else user_dept

    # ✅ Lấy danh sách user theo khoa
    if user_role == 'admin':
        users = User.query.filter(User.department == selected_department).order_by(User.name).all() if selected_department else []
    else:
        users = [User.query.get(current_user_id)]

    # ✅ Xử lý tạo đơn nghỉ
    if request.method == 'POST' and 'user_id' in request.form:
        user_id_str = request.args.get('user_id')
        if user_id_str and user_id_str.isdigit():
            user_id = int(user_id_str)
        else:
            user_id = None  # hoặc xử lý giá trị mặc định
        user_id_str = request.form.get('user_id', '').strip()
        if not user_id_str.isdigit():
            flash("❌ Vui lòng chọn nhân viên hợp lệ.", "danger")
            return redirect('/leaves/add')

        user_id = int(user_id_str)
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        reason = request.form.get('reason')
        location = request.form.get('location')

        birth_day = request.form.get('birth_day')
        birth_month = request.form.get('birth_month')
        birth_year = request.form.get('birth_year')
        birth_date_str = f"{birth_year}-{birth_month.zfill(2)}-{birth_day.zfill(2)}"
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        start_work_year = int(request.form.get('start_work_year'))

        user = User.query.get(user_id)
        user.start_year = start_work_year

        leave = LeaveRequest(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            location=location,
            birth_date=birth_date
        )
        db.session.add(leave)
        db.session.commit()
        flash("✅ Đã tạo đơn nghỉ phép thành công.", "success")
        return redirect('/leaves')

    # ✅ Đơn vị để in ra trong form (nếu cần)
    unit = get_unit_config()

    return render_template(
        'add_leave.html',
        departments=departments,
        selected_department=selected_department,
        users=users,
        current_user_role=user_role,
        now=datetime.now()
    )

from models.leave_request import LeaveRequest

from datetime import datetime


@property
def full_name(self):
    return self.user.name

@property
def position(self):
    return self.user.position

@property
def birth_year(self):
    return self.birth_date.year if self.birth_date else ""

@property
def start_work_year(self):
    return self.user.start_year if hasattr(self.user, 'start_year') else ""

@property
def leave_days(self):
    return (self.end_date - self.start_date).days + 1

@app.route('/leaves/delete/<int:leave_id>')
def delete_leave(leave_id):
    leave = LeaveRequest.query.get_or_404(leave_id)
    db.session.delete(leave)
    db.session.commit()
    flash('Đã xoá đơn nghỉ phép thành công.', 'success')
    return redirect(url_for('view_leaves'))

from flask import request, render_template, redirect, session
from collections import defaultdict
import csv
import os
from models import User  # ✅ đúng

@app.route("/yeu-cau-xu-ly-cong-viec", methods=["GET", "POST"])
def yeu_cau_xu_ly_cong_viec():
    if request.method == "POST":
        ngay_thang = request.form.get("ngay_thang")
        khoa = request.form.get("khoa")
        nguoi_yeu_cau = request.form.get("nguoi_yeu_cau")
        chu_ky = request.form.get("chu_ky")
        loi = request.form.get("loi")
        so_ho_so = request.form.get("so_ho_so", "")
        so_phieu = request.form.get("so_phieu", "")
        noi_dung = request.form.get("noi_dung", "")
        xac_nhan = request.form.get("xac_nhan")

        def mark(name):
            return "✓" if xac_nhan == name else "✗"
        mark_hoa = mark("Hòa")
        mark_hiep = mark("Hiệp")
        mark_anh = mark("Ánh")
        mark_nam = mark("Nam")

        file_exists = os.path.isfile("data.csv")
        with open("data.csv", "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "NGÀY THÁNG", "KHOA / PHÒNG", "LỖI", "SỐ HỒ SƠ", "SỐ PHIẾU", "NỘI DUNG YÊU CẦU CV",
                    "TÊN NGƯỜI YÊU CẦU", "CHỮ KÝ", "HOÀ", "HIỆP", "ÁNH", "NAM"
                ])
            writer.writerow([
                ngay_thang, khoa, loi, so_ho_so, so_phieu, noi_dung,
                nguoi_yeu_cau, chu_ky, mark_hoa, mark_hiep, mark_anh, mark_nam
            ])
        return redirect("/yeu-cau-xu-ly-cong-viec")

    # ✅ Tạo dict nhân sự theo khoa
    staff_by_unit = defaultdict(list)
    users = User.query.filter(User.department != None).all()
    for user in users:
        if user.name and user.department:
            staff_by_unit[user.department].append(user.name)
    for dept in staff_by_unit:
        staff_by_unit[dept].sort()

    user_role = session.get('role')
    user_dept = session.get('department')

    if user_role in ['user', 'manager']:
        staff_by_unit_filtered = {user_dept: staff_by_unit.get(user_dept, [])}
        current_department = user_dept
    else:
        staff_by_unit_filtered = dict(staff_by_unit)
        current_department = ""

    return render_template(
        "form.html",
        staff_by_unit=staff_by_unit_filtered,
        current_department=current_department
    )

@app.route('/api/user-phones')
def api_user_phones():
    users = User.query.filter(User.department == 'Phòng Kế hoạch TH - CNTT').all()
    result = {user.name: user.phone for user in users if user.phone}
    return result

@app.route("/danh-sach-yeu-cau")
def danh_sach_yeu_cau():
    import csv
    import os
    from datetime import datetime

    data = []
    if os.path.exists("data.csv"):
        with open("data.csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader, [])
            for row in reader:
                if row:
                    try:
                        # Chuyển định dạng cột ngày (cột 0) nếu là yyyy-mm-dd
                        dt_parts = row[0].split("-")
                        if len(dt_parts) == 3:
                            row[0] = f"{dt_parts[2]}/{dt_parts[1]}/{dt_parts[0]}"
                    except:
                        pass
                    data.append(row)
    else:
        headers = []

    month = datetime.today().month

    # Tạo biến current_date với định dạng yêu cầu
    now = datetime.today()
    current_date = f"Gia Lai, ngày {now.day:02d} tháng {now.month:02d} năm {now.year}"

    return render_template(
        "danh_sach_yeu_cau.html",
        headers=headers,
        data=data,
        month=month,
        current_date=current_date
    )

@app.route("/xoa-yeu-cau/<int:index>", methods=["POST"])
def xoa_yeu_cau(index):
    import csv
    file_path = "data.csv"

    if not os.path.exists(file_path):
        return redirect("/danh-sach-yeu-cau")

    with open(file_path, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
        headers = rows[0]
        data = rows[1:]

    if 0 <= index < len(data):
        del data[index]  # Xóa dòng dữ liệu theo chỉ số

        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)

        return redirect("/danh-sach-yeu-cau")

from flask import send_file
import pandas as pd

@app.route('/xuat-excel')
def xuat_excel():
    try:
        df = pd.read_csv("data.csv", encoding="utf-8")
        file_path = "yeu_cau_cong_viec.xlsx"
        df.to_excel(file_path, index=False)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return f"Lỗi khi xuất Excel: {str(e)}"

from flask import render_template
from datetime import datetime
from models.leave_request import LeaveRequest
import os

@app.route('/leaves/print/<int:id>')
@login_required
def print_leave(id):
    from models.leave_request import LeaveRequest
    from utils.unit_config import get_unit_config
    leave = LeaveRequest.query.get_or_404(id)
    user = leave.user
    unit = get_unit_config()  # ✅ bắt buộc phải có

    return render_template(
        'leave_print.html',
        leave=leave,
        user=user,
        now=datetime.now()
    )

from flask import send_file
from io import BytesIO
from docx import Document
from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH

@app.route('/leaves/word/<int:leave_id>')
def export_leave_word(leave_id):
    from models.leave_request import LeaveRequest
    from models.user import User

    leave = LeaveRequest.query.get_or_404(leave_id)
    user = User.query.get(leave.user_id)

    document = Document()

    # Đặt font chữ mặc định cho toàn bộ văn bản
    style = document.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(14)
    font.element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')

    # Header: bảng 2 cột
    table = document.add_table(rows=1, cols=2)
    table.autofit = False
    table.columns[0].width = Pt(260)
    table.columns[1].width = Pt(260)
    cells = table.rows[0].cells

    # BÊNH VIỆN NHI TỈNH GIA LAI + Phòng ban (in hoa, in đậm, border bottom)
    p_left = cells[0].paragraphs[0]
    p_left.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p_left.add_run("BỆNH VIỆN NHI TỈNH GIA LAI\n")
    run.bold = True
    run.font.size = Pt(13)
    run = p_left.add_run(user.department.upper())
    run.bold = True
    run.font.size = Pt(14)

    # Border bottom cho đoạn bên trái
    p = p_left._p
    pPr = p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '4')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '000000')
    pBdr.append(bottom)
    pPr.append(pBdr)

    # CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM + Độc lập - Tự do - Hạnh phúc
    p_right = cells[1].paragraphs[0]
    p_right.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p_right.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n")
    run.bold = True
    run.font.size = Pt(14)
    run = p_right.add_run("Độc lập - Tự do - Hạnh phúc")
    run.bold = True
    run.italic = True
    run.font.size = Pt(14)
    run.font.underline = True

    document.add_paragraph()  # Dòng trống

    # Tiêu đề chính giữa
    title = document.add_paragraph("ĐƠN XIN NGHỈ PHÉP")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = title.runs[0]
    run_title.bold = True
    run_title.font.size = Pt(14)
    run_title.text = run_title.text.upper()

    # Kính gửi (in nghiêng, đậm, thụt lề 1cm)
    p_kg = document.add_paragraph()
    p_kg.paragraph_format.left_indent = Pt(28)
    run_kg = p_kg.add_run("Kính gửi:")
    run_kg.bold = True
    run_kg.italic = True
    run_kg.font.size = Pt(14)

    # Danh sách kính gửi, thụt lề 3cm
    p_list = document.add_paragraph()
    p_list.paragraph_format.left_indent = Pt(85)
    p_list.paragraph_format.line_spacing = 1.4
    p_list.add_run("- Giám đốc Bệnh viện Nhi tỉnh Gia Lai\n")
    p_list.add_run("- Phòng Tổ chức - Hành chính quản trị\n")
    p_list.add_run(f"- {user.department}")

    # Thông tin người làm đơn
    p_name = document.add_paragraph()
    p_name.add_run("Tên tôi là: ").font.size = Pt(14)
    run_name = p_name.add_run(user.name.upper())
    run_name.bold = True
    run_name.font.size = Pt(14)
    p_name.add_run("    Sinh ngày: ").font.size = Pt(14)
    run_birth = p_name.add_run(leave.birth_date.strftime('%d/%m/%Y') if leave.birth_date else '')
    run_birth.bold = True
    run_birth.font.size = Pt(14)

    p_pos = document.add_paragraph()
    p_pos.add_run(f"Chức vụ: {user.position}    ").font.size = Pt(14)
    p_pos.add_run("Năm vào công tác: ......................").font.size = Pt(14)

    p_dep = document.add_paragraph(f"Đơn vị công tác: {user.department} - Bệnh viện Nhi tỉnh Gia Lai")
    p_dep.style.font.size = Pt(14)

    # Nội dung đơn
    document.add_paragraph(
        "Nay tôi làm đơn này trình Ban Giám đốc, Phòng Tổ chức - Hành chính quản trị xem xét và sắp xếp cho tôi được nghỉ phép.")
    document.add_paragraph(
        f"Thời gian nghỉ: từ ngày {leave.start_date.strftime('%d/%m/%Y')} đến ngày {leave.end_date.strftime('%d/%m/%Y')}.")
    document.add_paragraph(f"Lý do: {leave.reason}")
    document.add_paragraph(f"Nơi nghỉ phép: {leave.location}")
    document.add_paragraph("Tôi xin cam đoan sẽ bàn giao công việc đầy đủ và trở lại làm việc đúng thời gian quy định.")
    document.add_paragraph("Vậy kính mong các cấp giải quyết, tôi xin chân thành cảm ơn./.")

    # Footer ngày tháng căn phải, in nghiêng
    date_str = leave.start_date.strftime("Gia Lai, ngày %d tháng %m năm %Y") if leave.start_date else ""
    p_footer = document.add_paragraph(date_str)
    p_footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_footer.runs[0].italic = True
    p_footer.runs[0].font.size = Pt(14)

    # Bảng ký tên 3 cột căn giữa
    sign_table = document.add_table(rows=2, cols=3)
    sign_table.autofit = False
    widths = [Pt(180), Pt(180), Pt(180)]
    for idx, width in enumerate(widths):
        sign_table.columns[idx].width = width

    # Dòng 1
    cells = sign_table.rows[0].cells
    cells[0].text = user.department.upper()
    cells[1].text = "Người làm đơn"
    cells[2].text = "Giám đốc\nPhòng Tổ chức – HC QT"
    for cell in cells:
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.font.size = Pt(14)
                run.bold = True

    # Dòng 2
    cells = sign_table.rows[1].cells
    cells[0].text = ""
    cells[1].text = "(Ký và ghi rõ họ tên)"
    cells[2].text = ""
    for cell in cells:
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.font.size = Pt(14)
                run.italic = True

    # Tên người làm đơn căn giữa phía dưới bảng ký
    p_name_sign = document.add_paragraph(user.name.upper())
    p_name_sign.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_name_sign.runs[0].font.size = Pt(14)

    # Xuất file Word
    stream = BytesIO()
    document.save(stream)
    stream.seek(0)

    return send_file(
        stream,
        as_attachment=True,
        download_name=f"don_nghi_phep_{leave.id}.docx",
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@app.route('/test-export')
def test_export():
    return "Route hoạt động"

@app.route('/assign', methods=['GET', 'POST'])
def assign_schedule():
    user_role = session.get('role')
    user_dept = session.get('department')

    if user_role != 'admin':
        departments = [user_dept]
    else:
        departments = [d[0] for d in db.session.query(User.department).filter(User.department != None).distinct().all()]

    selected_department = request.args.get('department') if request.method == 'GET' else request.form.get('department')
    users = User.query.filter_by(department=selected_department).all() if selected_department else []
    shifts = Shift.query.all()
    leaves = []

    if request.method == 'POST':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        duplicated_entries = []

        user_name = session.get('name')
        app.logger.info(f"[ASSIGN] User '{user_name}' phân lịch '{selected_department}' từ {start_date} đến {end_date}")

        leaves = LeaveRequest.query.filter(
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date
        ).all()

        for checkbox in request.form.getlist('schedule'):
            user_id, shift_id = checkbox.split('-')
            user_id = int(user_id)
            shift_id = int(shift_id)

            current = start_date
            while current <= end_date:
                existing = Schedule.query.filter_by(user_id=user_id, shift_id=shift_id, work_date=current).first()

                if existing:
                    duplicated_entries.append(f"{existing.user.name} đã có lịch ca {existing.shift.name} ngày {current.strftime('%d/%m/%Y')}")
                else:
                    new_schedule = Schedule(user_id=user_id, shift_id=shift_id, work_date=current)
                    db.session.add(new_schedule)

                current += timedelta(days=1)

        try:
            db.session.commit()
            if duplicated_entries:
                for message in duplicated_entries:
                    flash(f"⚠️ {message}", "danger")
            else:
                flash("✅ Đã lưu lịch thành công.", "success")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"❌ Lỗi khi lưu lịch trực: {e}", exc_info=True)
            flash("❌ Lỗi máy chủ: không thể lưu lịch trực.", "danger")
            return redirect('/assign?department=' + selected_department)

        return redirect('/assign?department=' + selected_department)

    return render_template('assign.html',
        departments=departments,
        selected_department=selected_department,
        users=users,
        shifts=shifts,
        leaves=leaves
    )


@app.route('/auto-assign')
def auto_assign_page():
    selected_department = request.args.get('department')

    departments = db.session.query(User.department).distinct().all()
    departments = [d[0] for d in departments if d[0]]

    users = User.query.filter_by(department=selected_department).all() if selected_department else []
    shifts = Shift.query.all()

    user_name = session.get('name')  # ✅ Thêm dòng này
    app.logger.info(f"[AUTO_ASSIGN_VIEW] User '{user_name}' mở trang phân lịch nhanh cho khoa '{selected_department}'")

    return render_template('auto_assign.html',
                           departments=departments,
                           selected_department=selected_department,
                           users=users,
                           shifts=shifts)

def get_departments():
    return [d[0] for d in db.session.query(User.department).distinct().all() if d[0]]

@app.route('/auto-attendance', methods=['GET', 'POST'])
def auto_attendance_page():
    from models.user import User
    from models.shift import Shift
    from models.schedule import Schedule  # model lịch trực
    from models.attendance import Attendance
    from datetime import datetime, timedelta
    from flask import request, redirect, url_for, flash, render_template, session

    departments = get_departments()

    if request.method == 'POST':
        selected_department = request.form.get('department')
    else:
        selected_department = request.args.get('department')

    day_shifts = Shift.query.filter(Shift.name.ilike('%làm ngày%')).all()

    if selected_department:
        users = User.query.filter_by(department=selected_department).order_by(User.name).all()
    else:
        users = []

    if request.method == 'POST':
        selected_department = request.form.get('department')
        user_name = session.get('name')  # 👈 Đặt lên đầu để tránh lỗi
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        shift_code = request.form.get('shift_code')
        staff_ids = request.form.getlist('staff_ids')

        app.logger.info(f"[AUTO_ATTEND_START] User '{user_name}' bắt đầu tạo lịch trực {shift_code} cho khoa '{selected_department}' từ {start_date_str} đến {end_date_str} cho {len(staff_ids)} nhân viên.")

        if not (selected_department and start_date_str and end_date_str and shift_code and staff_ids):
            flash('Vui lòng chọn đầy đủ thông tin.', 'danger')
            return redirect(url_for('auto_attendance_page'))

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        shift = Shift.query.filter_by(code=shift_code).first()
        if not shift:
            flash('Ca làm không hợp lệ.', 'danger')
            return redirect(url_for('auto_attendance_page'))

        staff_members = User.query.filter(User.id.in_(staff_ids)).all()

        current_date = start_date
        try:
            created_count = 0
            while current_date <= end_date:
                weekday = current_date.weekday()  # 0 = Thứ 2, ..., 6 = Chủ nhật

                # Bỏ qua Thứ 7, CN
                if weekday in [5, 6]:
                    current_date += timedelta(days=1)
                    continue

                # Bỏ qua nếu là ngày lễ cố định
                ngay_le = {'01-01', '04-30', '05-01', '09-02'}
                if current_date.strftime('%m-%d') in ngay_le:
                    current_date += timedelta(days=1)
                    continue


                for staff in staff_members:
                    existing = Schedule.query.filter_by(
                        user_id=staff.id,
                        work_date=current_date
                    ).first()
                    if not existing:
                        schedule = Schedule(
                            user_id=staff.id,
                            work_date=current_date,
                            shift_id=shift.id
                        )
                        db.session.add(schedule)
                        created_count += 1

                current_date += timedelta(days=1)

            db.session.commit()
            app.logger.info(f"[AUTO_ATTEND_DONE] Đã tạo {created_count} dòng chấm công tự động thành công.")

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"[AUTO_ATTEND_ERROR] Lỗi khi tạo lịch trực: {e}")
            flash(f'Lỗi khi lưu lịch trực: {e}', 'danger')
            return redirect(url_for('auto_attendance_page', department=selected_department))

        flash(f'Đã tạo lịch trực cho {len(staff_members)} nhân viên từ {start_date} đến {end_date}.', 'success')
        return redirect(url_for('auto_attendance_page', department=selected_department))

    return render_template('auto_attendance.html',
                           departments=departments,
                           selected_department=selected_department,
                           users=users,
                           day_shifts=day_shifts)


@app.route('/sync-attendance', methods=['POST'])
def sync_attendance():
    from models.schedule import Schedule
    from models.attendance import Attendance
    from models.user import User
    from datetime import datetime
    from flask import request, flash, redirect, url_for
    from extensions import db

    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    department = request.form.get('department')

    if not (start_date_str and end_date_str and department):
        flash('Vui lòng cung cấp đủ thông tin: khoa, từ ngày, đến ngày.', 'danger')
        return redirect(url_for('auto_attendance_page'))

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

    # Lấy tất cả lịch trực trong khoảng ngày và khoa được chọn
    schedules = Schedule.query.join(Schedule.user).filter(
        User.department == department,
        Schedule.work_date >= start_date,
        Schedule.work_date <= end_date
    ).all()

    # Xóa dữ liệu Attendance cũ trong khoảng thời gian và khoa để tránh trùng lặp
    Attendance.query.filter(
        Attendance.department == department,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).delete()

    # Thêm dữ liệu Attendance mới dựa trên Schedule
    for schedule in schedules:
        attendance = Attendance(
            user_id=schedule.user_id,
            date=schedule.work_date,
            shift_id=schedule.shift_id,
            department=department,
            status='Công'
        )
        db.session.add(attendance)

    db.session.commit()
    flash(f'Đã đồng bộ {len(schedules)} bản ghi lịch trực sang bảng chấm công.', 'success')
    return redirect(url_for('auto_attendance_page', department=department))

from flask import Flask, request, render_template, redirect, url_for, flash, session
from datetime import datetime, timedelta
from extensions import db
from models.user import User
from models.shift import Shift
from models.schedule import Schedule

from utils.unit_config import get_unit_config

@app.route('/schedule', methods=['GET', 'POST'])
def view_schedule():
    user_role = session.get('role')
    user_dept = session.get('department')

    # Quyết định khoa được chọn
    if user_role == 'admin':
        selected_department = request.args.get('department')
    else:
        # Manager và user luôn xem khoa của mình
        selected_department = user_dept

    # Danh sách khoa
    if user_role == 'admin':
        departments = [d[0] for d in db.session.query(User.department)
                       .filter(User.department.isnot(None)).distinct().all()]
    else:
        departments = [user_dept] if user_dept else []

    # Ngày bắt đầu và kết thúc
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    else:
        start_date = datetime.today().date()
        end_date = start_date + timedelta(days=6)

    # Lấy lịch trực
    query = Schedule.query.join(User).join(Shift)\
        .filter(Schedule.work_date.between(start_date, end_date))
    if selected_department:
        query = query.filter(User.department == selected_department)

    schedules = query.order_by(Schedule.work_date).all()
    print(">>> Các ngày có lịch trực:", sorted({s.work_date for s in schedules}))
    date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    # Chuẩn bị dữ liệu lịch trực
    schedule_data = {}
    for s in schedules:
        u = s.user
        if u.id not in schedule_data:
            schedule_data[u.id] = {
                'id': u.id,
                'name': u.name,
                'position': u.position,
                'department': u.department,
                'shifts': {},
                'shifts_full': {}
            }
        # Cho phép nhiều ca/ngày
        if s.work_date not in schedule_data[u.id]['shifts_full']:
            schedule_data[u.id]['shifts_full'][s.work_date] = []
        schedule_data[u.id]['shifts_full'][s.work_date].append({
            'shift_id': s.shift.id,
            'shift_name': s.shift.name
        })

    # Dữ liệu lọc riêng cho in
    filtered_for_print = {}
    for uid, data in schedule_data.items():
        filtered_shifts = {}
        for work_date, shifts in data['shifts_full'].items():
            ca_truc = [
                ca for ca in shifts 
                if 'trực' in ca['shift_name'].lower() and 'nghỉ' not in ca['shift_name'].lower()
            ]
            if ca_truc:
                filtered_shifts[work_date] = ca_truc

        if filtered_shifts:
            filtered_for_print[uid] = {
                'id': data['id'],
                'name': data['name'],
                'position': data['position'],
                'department': data['department'],
                'shifts_full': filtered_shifts
            }

    # Kiểm tra chữ ký
    signature = ScheduleSignature.query.filter_by(
        department=selected_department,
        from_date=start_date,
        to_date=end_date
    ).first()
    is_signed = bool(signature)
    signed_at = signature.signed_at if signature else None

    # Kiểm tra khóa
    lock = ScheduleLock.query.filter_by(
        department=selected_department,
        start_date=start_date,
        end_date=end_date
    ).first()
    locked = bool(lock)

    return render_template(
        'schedule.html',
        departments=departments,
        selected_department=selected_department,
        schedule_data=schedule_data,           # 👉 dữ liệu đầy đủ cho bảng chính
        print_data=filtered_for_print,         # 👉 chỉ dùng khi cần riêng (Excel, xuất in khác)
        date_range=date_range,
        start_date=start_date,
        end_date=end_date,
        now=datetime.now(),
        is_signed=is_signed,
        signed_at=signed_at,
        locked=locked,
        user={
            'role': user_role,
            'department': user_dept,
            'name': session.get('name')
        }
    )                                                             

@app.route('/schedule/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user_schedule(user_id):
    user = User.query.get_or_404(user_id)
    shifts = Shift.query.all()
    schedules = Schedule.query.filter_by(user_id=user_id).all()

    # ✅ Kiểm tra nếu bất kỳ ca trực nào đã bị khóa thì không cho sửa
    for s in schedules:
        is_locked = ScheduleLock.query.filter_by(department=user.department) \
            .filter(ScheduleLock.start_date <= s.work_date,
                    ScheduleLock.end_date >= s.work_date).first()
        if is_locked:
            return "Không thể chỉnh sửa. Lịch trực đã được ký xác nhận và khóa.", 403

    if request.method == 'POST':
        edited_dates = []  # ✅ THÊM DÒNG NÀY

        for s in schedules:
            new_shift_id = request.form.get(f'shift_{s.id}')
            if new_shift_id and int(new_shift_id) != s.shift_id:
                edited_dates.append((s.work_date, s.shift_id, int(new_shift_id)))  # Ghi nhận thay đổi
                s.shift_id = int(new_shift_id)

        db.session.commit()

        # 🔎 Ghi log nếu có chỉnh sửa
        if edited_dates:
            user_name = session.get('name')
            for date, old_id, new_id in edited_dates:
                app.logger.info(f"[EDIT] User '{user_name}' chỉnh sửa lịch user_id={user_id} - ngày {date}, từ ca {old_id} → ca {new_id}")

        return redirect('/schedule')

    return render_template('edit_schedule.html', user=user, shifts=shifts, schedules=schedules)

@app.route('/schedule/delete-one', methods=['POST'])
def delete_one_schedule():
    role = session.get('role')
    if role not in ['admin', 'manager']:
        return "Bạn không có quyền xoá ca trực.", 403

    user_id = request.form.get('user_id')
    shift_id = request.form.get('shift_id')
    work_date = request.form.get('work_date')
    department = session.get('department') if role == 'manager' else request.form.get('department')

    work_date_obj = datetime.strptime(work_date, '%Y-%m-%d').date()

    lock = ScheduleLock.query.filter_by(department=department)\
        .filter(ScheduleLock.start_date <= work_date_obj, ScheduleLock.end_date >= work_date_obj).first()
    if lock and role == 'manager':
        return "Bảng lịch đã ký xác nhận. Vui lòng liên hệ Admin để sửa.", 403

    schedule = Schedule.query.filter_by(
        user_id=user_id,
        shift_id=shift_id,
        work_date=work_date
    ).first()

    if schedule:
        db.session.delete(schedule)
        db.session.commit()

    return redirect(request.referrer or '/schedule')

@app.route('/schedule/sign', methods=['POST'])
@login_required
def sign_schedule():
    department = request.form.get('department')
    from_date_str = request.form.get('from_date')
    to_date_str = request.form.get('to_date')

    user_name = session.get('name')
    app.logger.info(f"[SIGN] User '{user_name}' ký lịch trực cho khoa '{department}' từ {from_date_str} đến {to_date_str}")

    if not department or not from_date_str or not to_date_str:
        flash("Thiếu thông tin để ký xác nhận.", "danger")
        return redirect('/schedule')

    from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
    to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()

    # Kiểm tra đã ký chưa
    existing = ScheduleSignature.query.filter_by(
        department=department,
        from_date=from_date,
        to_date=to_date
    ).first()

    if existing:
        flash("📌 Bảng lịch trực này đã được ký xác nhận trước đó.", "info")
    else:
        signed_by = session.get('user_id')
        new_sig = ScheduleSignature(
            department=department,
            from_date=from_date,
            to_date=to_date,
            signed_by=signed_by,
            signed_at=datetime.now()
        )
        db.session.add(new_sig)
        db.session.commit()
        flash("✅ Đã ký xác nhận và khóa bảng lịch trực.", "success")

    return redirect('/schedule?department={}&start_date={}&end_date={}'.format(
        department, from_date_str, to_date_str
    ))

@app.route('/schedule/unsign', methods=['POST'])
@admin_required
def unsign_schedule():
    department = request.form['department']
    from_date = request.form['from_date']
    to_date = request.form['to_date']

    user_name = session.get('name')
    app.logger.info(f"[UNSIGN] Admin '{user_name}' hủy ký lịch khoa '{department}' từ {from_date} đến {to_date}")

    schedules = ScheduleAssignment.query.filter(
        ScheduleAssignment.department == department,
        ScheduleAssignment.date >= from_date,
        ScheduleAssignment.date <= to_date
    ).all()

    for sched in schedules:
        sched.is_signed = False
        sched.signed_at = None
        sched.signed_by = None

    db.session.commit()
    flash("🗑️ Đã hủy ký xác nhận. Có thể chỉnh sửa lịch trực.", "warning")
    return redirect('/schedule')

@app.route('/schedule/unlock', methods=['POST'])
def unlock_signature():
    if session.get('role') != 'admin':
        return "Bạn không có quyền thực hiện hành động này.", 403

    department = request.form.get('department')
    from_date = datetime.strptime(request.form.get('from_date'), '%Y-%m-%d').date()
    to_date = datetime.strptime(request.form.get('to_date'), '%Y-%m-%d').date()

    sig = ScheduleSignature.query.filter_by(
        department=department,
        from_date=from_date,
        to_date=to_date
    ).first()

    if sig:
        db.session.delete(sig)
        db.session.commit()
        flash("🧹 Đã hủy xác nhận và mở khóa lịch trực.", "warning")
    else:
        flash("Không tìm thấy bản ký xác nhận để hủy.", "danger")

    return redirect(f'/schedule?department={department}&start_date={from_date}&end_date={to_date}')

@app.route('/calendar')
def fullcalendar():
    selected_department = request.args.get('department')
    if session.get('role') in ['manager', 'user']:
        selected_department = session.get('department')

    departments = [d[0] for d in db.session.query(User.department).filter(User.department != None).distinct().all()]
    query = Schedule.query.join(User)

    if selected_department:
        query = query.filter(User.department == selected_department)

    schedules = query.order_by(Schedule.work_date).all()
    return render_template('fullcalendar.html',
                           schedules=schedules,
                           departments=departments,
                           selected_department=selected_department)

@app.route('/stats')
def stats():
    from sqlalchemy import func

    user_role = session.get('role')
    user_dept = session.get('department')

    query_users = User.query
    query_schedules = Schedule.query.join(User)

    if user_role in ['manager', 'user']:
        query_users = query_users.filter(User.department == user_dept)
        query_schedules = query_schedules.filter(User.department == user_dept)


    total_users = query_users.count()
    total_shifts = Shift.query.count()
    total_schedules = query_schedules.count()

    schedules_per_user = db.session.query(User.name, func.count(Schedule.id))\
        .join(Schedule)\
        .filter(User.department == user_dept if user_role != 'admin' else True)\
        .group_by(User.id).all()

    return render_template('stats.html',
                           total_users=total_users,
                           total_shifts=total_shifts,
                           total_schedules=total_schedules,
                           schedules_per_user=schedules_per_user)


@app.route('/report-by-department')
def report_by_department():
    user_role = session.get('role')
    user_dept = session.get('department')

    query = Schedule.query.join(User).join(Shift)
    if user_role in ['manager', 'user']:
        query = query.filter(User.department == user_dept)

    schedules = query.all()
    report = {}

    for s in schedules:
        dept = s.user.department
        if dept not in report:
            report[dept] = []
        report[dept].append(s)

    return render_template('report_by_department.html', report=report)

@app.route('/users-by-department')
def users_by_department():
    user_role = session.get('role')
    user_dept = session.get('department')
    user_name = session.get('name')

    selected_department = request.args.get('department')
    
    if user_role in ['manager', 'user']:
        # Nhân viên hoặc trưởng khoa chỉ xem khoa mình
        users = User.query.filter(
            User.department == user_dept,
            User.active == True
        ).order_by(User.name).all()
        departments = [user_dept]
        selected_department = user_dept
    else:
        # Admin có thể chọn khoa bất kỳ
        departments = [
            d[0] for d in db.session.query(User.department)
            .filter(User.department != None)
            .distinct()
            .all()
        ]
        if selected_department:
            users = User.query.filter(
                User.department == selected_department
            ).order_by(User.name).all()
        else:
            users = User.query.filter(
                User.active == True
            ).order_by(User.department, User.name).all()

    app.logger.info(f"[USER_VIEW] User '{user_name}' ({user_role}) xem danh sách nhân sự khoa '{selected_department}'")

    return render_template(
        'users_by_department.html',
        users=users,
        departments=departments,
        selected_department=selected_department,
        current_user_role=user_role
    )

@app.route('/users/inactive')
def inactive_users():
    users = User.query.filter_by(active=False).all()
    return render_template('inactive_users.html', users=users)

@app.route('/users/reactivate/<int:user_id>')
def reactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    user.active = True
    db.session.commit()
    flash("✅ Nhân viên đã được khôi phục!", "success")
    return redirect('/users/inactive')

@app.route('/users/deactivate/<int:user_id>')
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    user.active = False
    db.session.commit()
    flash("🚫 Nhân viên đã được ngừng hoạt động!", "warning")
    return redirect(request.referrer or url_for('users_by_department'))

@app.route('/users/delete-all', methods=['POST'])
def delete_all_users():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Không có quyền thực hiện chức năng này.", "danger")
        return redirect('/login')

    try:
        from models.user import User
        users_to_delete = User.query.filter(User.username != 'admin').all()
        print(f"🧹 Xoá {len(users_to_delete)} nhân sự...")  # ← ghi log số lượng
        app.logger.info(f"[USER_VIEW] User '{user_name}' ({user_role}) xem danh sách nhân sự khoa '{selected_department}'")

        for u in users_to_delete:
            print(f"→ Xoá: {u.username}")
            db.session.delete(u)

        db.session.commit()
        print("✅ Xoá xong.")
        flash("Đã xoá toàn bộ nhân sự (trừ admin).", "success")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Lỗi khi xoá: {str(e)}")  # ← chắc chắn sẽ in ra nếu lỗi
        flash(f"Lỗi khi xoá: {str(e)}", "danger")

    return redirect('/users-by-department')

@app.route('/export-by-department', methods=['GET', 'POST'])
def export_by_department():
    from sqlalchemy import distinct

    user_role = session.get('role')
    user_dept = session.get('department')

    # Lấy danh sách khoa
    departments = [d[0] for d in db.session.query(distinct(User.department)).filter(User.department != None).all()]
    selected_department = request.form.get('department') if request.method == 'POST' else user_dept

    if user_role != 'admin':
        selected_department = user_dept

    # Tạo file Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['Họ tên', 'Ca trực', 'Ngày trực'])

    # Truy vấn lịch có chứa từ "trực"
    query = Schedule.query.join(User).join(Shift).filter(Shift.name.ilike('%trực%'))

    if selected_department:
        query = query.filter(User.department == selected_department)

    schedules = query.order_by(Schedule.work_date).all()

    for s in schedules:
        if s.user and s.shift:
            ws.append([s.user.name, s.shift.name, s.work_date.strftime('%Y-%m-%d')])

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return send_file(stream, as_attachment=True, download_name="lichtruc_theo_khoa.xlsx")

@app.route('/generate_schedule', methods=['GET', 'POST'])
def generate_schedule_route():
    from models.leave_request import LeaveRequest

    departments = [d[0] for d in db.session.query(User.department)
                   .filter(User.department.isnot(None)).distinct().all()]

    if request.method == 'POST':
        department = request.form.get('department')
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        user_ids = request.form.getlist('user_ids')
        shift_ids = request.form.getlist('shift_ids')
        people_per_day = int(request.form.get('people_per_day', 1))

        if not user_ids or not shift_ids:
            flash("⚠️ Vui lòng chọn ít nhất 1 người và 1 ca trực.", "danger")
            return redirect(request.referrer)

        user_ids = [int(uid) for uid in user_ids]
        shift_ids = [int(sid) for sid in shift_ids]
        user_count = len(user_ids)

        date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
        assignments = []
        conflicts = []

        leaves = LeaveRequest.query.filter(
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date
        ).all()

        user_index = 0
        for work_date in date_range:
            assigned = set()
            for shift_id in shift_ids:
                attempts = 0
                while len(assigned) < people_per_day and attempts < user_count * 2:
                    uid = user_ids[user_index % user_count]
                    user_index += 1
                    attempts += 1

                    # Kiểm tra nghỉ phép
                    if any(l.user_id == uid and l.start_date <= work_date <= l.end_date for l in leaves):
                        continue

                    # Trùng lịch
                    exists = Schedule.query.filter_by(user_id=uid, shift_id=shift_id, work_date=work_date).first()
                    if exists or uid in assigned:
                        continue

                    # ✅ Thêm
                    assignments.append(Schedule(user_id=uid, shift_id=shift_id, work_date=work_date))
                    assigned.add(uid)

        if assignments:
            db.session.add_all(assignments)
            db.session.commit()
            flash("✅ Đã tạo lịch trực tự động thành công.", "success")

        if not assignments:
            flash("⚠️ Không có lịch nào được tạo. Có thể do tất cả bị trùng hoặc nghỉ phép.", "warning")

        return redirect(url_for('generate_schedule_route'))

    # GET hiển thị form
    selected_department = request.args.get('department')
    users = User.query.filter_by(department=selected_department).all() if selected_department else []
    shifts = Shift.query.all()

    return render_template('generate_form.html',
                           departments=departments,
                           selected_department=selected_department,
                           users=users,
                           shifts=shifts)


@app.route('/export')
def export_excel():
    user_role = session.get('role')
    user_dept = session.get('department')
    wb.active = wb.active  # Đảm bảo chọn đúng sheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['Họ tên', 'Ca trực', 'Ngày trực'])
    ws.freeze_panes = "A2"  # ✅ Cố định hàng tiêu đề

    # Lấy lịch trực có chứa từ "trực"
    query = Schedule.query.join(User).join(Shift).filter(Shift.name.ilike('%trực%'))
    if user_role != 'admin':
        query = query.filter(User.department == user_dept)

    schedules = query.order_by(Schedule.work_date).all()
    for s in schedules:
        if s.user and s.shift:
            ws.append([s.user.name, s.shift.name, s.work_date.strftime('%Y-%m-%d')])

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return send_file(stream, as_attachment=True, download_name="lichtruc.xlsx")

@app.route('/shifts')
def list_shifts():
    shifts = Shift.query.all()
    return render_template('shifts.html', shifts=shifts)

from flask import render_template, request, redirect, flash
from datetime import datetime
from models import Shift  # đảm bảo đã import đúng

def parse_time_string(time_str):
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    raise ValueError("❌ Định dạng thời gian không hợp lệ. Vui lòng nhập HH:MM hoặc HH:MM:SS.")

@app.route('/shifts/add', methods=['GET', 'POST'])
def add_shift():
    if request.method == 'POST':
        name = request.form['name']
        code = request.form['code']
        duration = request.form['duration']

        try:
            start_time = parse_time_string(request.form['start_time'])
            end_time = parse_time_string(request.form['end_time'])
            duration = float(duration)
        except ValueError as e:
            flash(str(e), 'danger')  # 🟢 Thông báo lỗi bằng tiếng Việt tại đây
            return render_template('add_shift.html', old=request.form)

        shift = Shift(name=name, code=code, start_time=start_time, end_time=end_time, duration=duration)
        db.session.add(shift)
        db.session.commit()

        user_name = session.get('name')
        app.logger.info(f"[SHIFT_ADD] {user_name} thêm ca trực '{name}' (Mã: {code}, {start_time}-{end_time})")

        flash("✅ Đã thêm ca trực mới.", "success")
        return redirect('/shifts')

    return render_template('add_shift.html')

from flask import request, redirect, flash
import openpyxl
from datetime import datetime
from models.shift import Shift
from app import db

def parse_time_string(time_str):
    return datetime.strptime(time_str.strip(), '%H:%M').time()

from flask import flash, redirect, render_template

@app.route('/shifts/edit/<int:id>', methods=['GET', 'POST'])
def edit_shift(id):
    shift = Shift.query.get_or_404(id)
    old = {}

    if request.method == 'POST':
        old = {
            'code': request.form['code'],
            'name': request.form['name'],
            'start_time': request.form['start_time'],
            'end_time': request.form['end_time'],
            'duration': request.form['duration']
        }

        try:
            shift.code = old['code']
            shift.name = old['name']

            # Parse giờ HH:MM hoặc HH:MM:SS
            try:
                shift.start_time = datetime.strptime(old['start_time'], '%H:%M').time()
            except ValueError:
                shift.start_time = datetime.strptime(old['start_time'], '%H:%M:%S').time()

            try:
                shift.end_time = datetime.strptime(old['end_time'], '%H:%M').time()
            except ValueError:
                shift.end_time = datetime.strptime(old['end_time'], '%H:%M:%S').time()

            shift.duration = float(old['duration'])

            db.session.commit()

            user_name = session.get('name')
            app.logger.info(f"[SHIFT_EDIT] {user_name} sửa ca trực ID={id} thành tên: {shift.name}, mã: {shift.code}, giờ: {shift.start_time}-{shift.end_time}")

            return redirect('/shifts')

        except ValueError as ve:
            flash("⚠️ Vui lòng nhập giờ theo định dạng HH:MM hoặc HH:MM:SS", "danger")

    return render_template('edit_shift.html', shift=shift, old=old)

@app.route('/shifts/delete/<int:shift_id>')
def delete_shift(shift_id):
    shift = Shift.query.get_or_404(shift_id)

    from models.schedule import Schedule
    if Schedule.query.filter_by(shift_id=shift_id).first():
        return "Không thể xoá ca này vì đang được sử dụng trong lịch trực.", 400

    db.session.delete(shift)
    db.session.commit()

    user_name = session.get('name', 'Không xác định')
    app.logger.info(f"[SHIFT_DELETE] {user_name} đã xoá ca trực: {shift.name}")

    return redirect('/shifts')

@app.route('/export-shifts')
def export_shifts():
    import openpyxl
    from io import BytesIO
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Shifts"

    ws.append(["Tên ca", "Mã ca", "Giờ bắt đầu", "Giờ kết thúc", "Thời lượng"])

    for shift in Shift.query.order_by(Shift.name).all():
        ws.append([shift.name, shift.code, str(shift.start_time), str(shift.end_time), shift.duration])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="danh_sach_ca.xlsx")

from datetime import datetime, time
from flask import flash  # cần import để sử dụng thông báo

@app.route('/import-shifts', methods=['POST'])
def import_shifts_excel():  # ✅ Đổi tên hàm
    import openpyxl
    from datetime import datetime, time

    file = request.files['file']
    if not file:
        flash("Không có file được chọn.", "error")
        return redirect('/shifts')

    try:
        wb = openpyxl.load_workbook(file)
        ws = wb.active

        for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            name, code, start, end, duration = row
            if name and code:
                def to_time(val):
                    if isinstance(val, time):
                        return val
                    if isinstance(val, datetime):
                        return val.time()
                    if isinstance(val, str):
                        for fmt in ("%H:%M", "%H:%M:%S"):
                            try:
                                return datetime.strptime(val.strip(), fmt).time()
                            except ValueError:
                                continue
                    return None

                start_time = to_time(start)
                end_time = to_time(end)

                if not start_time or not end_time:
                    flash(f"Dòng {idx}: Giờ bắt đầu/kết thúc sai định dạng. Dùng 'HH:MM' hoặc 'HH:MM:SS'.", "error")
                    continue

                existing = Shift.query.filter_by(code=code).first()
                if not existing:
                    new_shift = Shift(name=name, code=code, start_time=start_time, end_time=end_time, duration=duration)
                    db.session.add(new_shift)

        db.session.commit()
        flash("✅ Đã nhập ca trực thành công.", "success")
    except Exception as e:
        flash(f"❌ Lỗi khi đọc file: {str(e)}", "error")

    return redirect('/shifts')

@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        new_username = request.form['username']
        if User.query.filter(User.username == new_username, User.id != user_id).first():
            error_message = "User này đã có người dùng, bạn không thể cập nhật."
            return render_template('edit_user.html', user=user, error=error_message)

        user.name = request.form['name']
        user.username = new_username
        user.password = request.form['password']
        user.role = request.form['role']
        user.department = request.form['department']
        user.position = request.form['position']
        user.contract_type = request.form.get('contract_type')  # ✅ nếu có thêm trường này
        user.phone = request.form['phone']
        db.session.commit()
        return redirect('/users-by-department')

    return render_template('edit_user.html', user=user)


@app.route('/users/add', methods=['GET', 'POST'])
def add_user():
    current_role = session.get('role')

    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        department = request.form['department']
        position = request.form['position']
        contract_type = request.form.get('contract_type')
        phone = request.form.get('phone')

        # ⚠️ Nếu là manager thì luôn ép vai trò nhân viên mới là 'user'
        if current_role == 'manager':
            role = 'user'

        # Kiểm tra trùng username
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("❌ Tên đăng nhập đã tồn tại. Vui lòng chọn tên khác.", "danger")
            return render_template('add_user.html', old=request.form)

        new_user = User(
            name=name,
            username=username,
            password=password,
            role=role,
            department=department,
            position=position,
            contract_type=contract_type,
            phone=phone,
        )
        db.session.add(new_user)
        db.session.commit()
        flash("✅ Đã thêm người dùng mới.", "success")
        return redirect('/users-by-department')

    return render_template('add_user.html')

@app.route('/import-users', methods=['GET', 'POST'])
def import_users():
    import openpyxl
    from sqlalchemy.exc import IntegrityError

    if request.method == 'POST':
        file = request.files['file']
        if file.filename.endswith('.xlsx'):
            wb = openpyxl.load_workbook(file)
            sheet = wb.active
            skipped_users = []
            imported_count = 0

            for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                if not any(row):
                    continue
                # Gán đúng thứ tự theo file:
                name          = row[0]
                username      = row[1]
                password      = row[2]
                role          = row[3]
                department    = row[4]
                position      = row[5]
                contract_type = row[6] if len(row) > 6 else None 
                phone         = row[7] if len(row) > 7 else None

                # Bỏ qua nếu thiếu tên đăng nhập hoặc đã tồn tại
                if not username or User.query.filter_by(username=username).first():
                    skipped_users.append(username or f"Hàng {idx}")
                    continue

                user = User(
                    name=name,
                    username=username,
                    password=password,
                    role=role,
                    department=department,
                    position=position,
                    contract_type=contract_type,
                    phone=phone
                )
                db.session.add(user)
                imported_count += 1

            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("❌ Lỗi khi lưu dữ liệu. Vui lòng kiểm tra nội dung file Excel.", "danger")
                return redirect('/users-by-department')

            if skipped_users:
                flash(f"⚠️ Đã nhập {imported_count} người dùng. Bỏ qua: {', '.join(skipped_users)}", "warning")
            else:
                flash(f"✅ Đã nhập thành công {imported_count} người dùng.", "success")

            return redirect('/users-by-department')
        else:
            flash("❌ Vui lòng chọn file Excel (.xlsx)", "danger")
            return redirect('/import-users')

    return render_template('import_users.html')

import logging
from datetime import datetime

# Thiết lập file log
logging.basicConfig(filename='phanquyen.log', level=logging.INFO)

@app.route('/roles', methods=['GET', 'POST'])
def manage_roles():
    if session.get('role') != 'admin':
        return "Bạn không có quyền truy cập trang này."

    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '')
    department_filter = request.args.get('department', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 10

    users_query = User.query
    if search:
        users_query = users_query.filter(User.name.ilike(f"%{search}%"))
    if role_filter:
        users_query = users_query.filter_by(role=role_filter)
    if department_filter:
        users_query = users_query.filter_by(department=department_filter)

    pagination = users_query.order_by(User.department).paginate(page=page, per_page=per_page)
    users = pagination.items

    modules = [
        'trang_chu', 'xem_lich_truc', 'yeu_cau_cv_ngoai_gio', 'don_nghi_phep',
        'xep_lich_truc', 'tong_hop_khth', 'cham_cong', 'bang_cong_gop', 'bang_tinh_tien_truc',
        'cau_hinh_ca_truc', 'thiet_lap_phong_kham', 'nhan_su_theo_khoa',
        'cau_hinh_tien_truc', 'thiet_lap_khoa_hscc', 'phan_quyen',
        'danh_sach_cong_viec', 'xem_log', 'doi_mat_khau', 'module_config'
    ]

    module_names = {
        'trang_chu': 'Trang chủ',
        'xem_lich_truc': 'Xem lịch trực',
        'yeu_cau_cv_ngoai_gio': 'Yêu cầu công việc ngoài giờ',
        'don_nghi_phep': 'Đơn nghỉ phép',
        'xep_lich_truc': 'Xếp lịch trực',
        'tong_hop_khth': 'Tổng hợp KHTH',
        'cham_cong': 'Chấm công',
        'bang_cong_gop': 'Bảng công gộp',
        'bang_tinh_tien_truc': 'Bảng thanh toán tiền trực',
        'cau_hinh_ca_truc': 'Cấu hình ca trực',
        'thiet_lap_phong_kham': 'Thiết lập Phòng khám',
        'nhan_su_theo_khoa': 'Nhân sự theo khoa',
        'cau_hinh_tien_truc': 'Cấu hình tiền trực',
        'thiet_lap_khoa_hscc': 'Thiết lập khoa HSCC',
        'phan_quyen': 'Phân quyền',
        'danh_sach_cong_viec': 'Danh sách yêu cầu công việc',
        'xem_log': 'Xem log hệ thống',
        'doi_mat_khau': 'Đổi mật khẩu',
        'module_config': 'Cấu hình phân hệ'
    }

    if request.method == 'POST':
        all_users = User.query.all()
        for user in all_users:
            selected_modules = request.form.getlist(f'modules_{user.id}[]')

            # Nếu không có modules gửi lên thì bỏ qua → không sửa phân quyền user đó
            if not selected_modules:
                continue

            role = request.form.get(f'role_{user.id}')
            dept = request.form.get(f'department_{user.id}')
            position = request.form.get(f'position_{user.id}')

            if role and dept and position:
                if (user.role != role) or (user.department != dept) or (user.position != position):
                    logging.info(f"{datetime.now()} | Admin ID {session['user_id']} cập nhật: {user.username} → "
                                 f"Role: {user.role} → {role}, Dept: {user.department} → {dept}, Position: {user.position} → {position}")
                user.role = role
                user.department = dept
                user.position = position

            # Xoá phân quyền cũ và thêm lại
            Permission.query.filter_by(user_id=user.id).delete()
            for mod in modules:
                db.session.add(Permission(
                    user_id=user.id,
                    module_name=mod,
                    can_access=(mod in selected_modules)
                ))

        db.session.commit()
        flash("✅ Đã lưu thay đổi phân quyền người dùng.", "success")
        return redirect('/roles')

    departments = [d[0] for d in db.session.query(User.department).distinct().all() if d[0]]
    roles = ['admin', 'manager', 'user']
    positions = [p[0] for p in db.session.query(User.position).filter(User.position != None).distinct().all()]

    for user in users:
        user.modules = [perm.module_name for perm in user.permissions if perm.can_access]

    return render_template('manage_roles.html',
                           users=users,
                           departments=departments,
                           roles=roles,
                           positions=positions,
                           modules=modules,
                           module_names=module_names,
                           pagination=pagination,
                           current_search=search,
                           current_role=role_filter,
                           current_department=department_filter)

@app.route('/unit-config', methods=['GET', 'POST'])
def unit_config():
    if session.get('role') != 'admin':
        return "Bạn không có quyền truy cập."

    config = UnitConfig.query.first()
    if not config:
        config = UnitConfig()

    if request.method == 'POST':
        config.name = request.form['name']
        config.address = request.form['address']
        config.phone = request.form['phone']
        db.session.add(config)
        db.session.commit()
        flash("✅ Đã cập nhật thông tin đơn vị", "success")
        return redirect('/unit-config')

    return render_template('unit_config.html', config=config)

from flask import send_file

@app.route('/view-log')
def view_log():
    if session.get('role') != 'admin':
        return "Không có quyền truy cập", 403

    log_path = os.path.join('logs', 'activity.log')
    if not os.path.exists(log_path):
        return render_template('view_log.html', log_lines=[])

    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    return render_template('view_log.html', log_lines=lines)

@app.route('/download-log')
def download_log():
    if session.get('role') != 'admin':
        return "Không có quyền tải log", 403

    log_path = os.path.join('logs', 'activity.log')
    return send_file(log_path, as_attachment=True)

@app.route('/clear-log', methods=['POST'])
def clear_log():
    if session.get('role') != 'admin':
        return "Không có quyền xoá log", 403

    log_path = os.path.join('logs', 'activity.log')
    open(log_path, 'w').close()
    return redirect('/view-log')


@app.route('/users/delete/<int:user_id>', methods=['POST', 'GET'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    user.active = False  # ✅ Đánh dấu ngừng hoạt động
    db.session.commit()
    flash("✅ Đã ngừng hoạt động nhân viên.", "success")
    return redirect('/users-by-department')

@app.route('/export-template', methods=['POST'])
def export_template():
    department = request.form.get('department')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    print(">>> [EXPORT] Khoa:", department)
    print(">>> [EXPORT] Từ ngày:", start_date)
    print(">>> [EXPORT] Đến ngày:", end_date)

    query = Schedule.query.join(User).join(Shift)

    if department:
        query = query.filter(User.department == department)

    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Schedule.work_date.between(start, end))
        except ValueError:
            return "Ngày không hợp lệ.", 400
    else:
        return "Vui lòng chọn khoảng thời gian.", 400

    schedules = query.order_by(Schedule.work_date).all()
    if not schedules:
        return "Không có dữ liệu lịch trực.", 404

    # Tập hợp ngày
    date_range = sorted({s.work_date for s in schedules})

    # Pivot dữ liệu người dùng
    schedule_data = {}
    for s in schedules:
        u = s.user
        if u.id not in schedule_data:
            schedule_data[u.id] = {
                'name': u.name,
                'position': u.position,
                'department': u.department,
                'shifts': {}
            }
        schedule_data[u.id]['shifts'][s.work_date] = s.shift.name

    # --- Tạo Excel ---
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lịch trực ngang"

    # --- Quốc hiệu, tiêu đề đầu trang ---
    ws.merge_cells('A1:G1')
    ws['A1'] = "BỆNH VIỆN NHI TỈNH GIA LAI"
    ws.merge_cells('H1:N1')
    ws['H1'] = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"
    ws.merge_cells('H2:N2')
    ws['H2'] = "Độc lập - Tự do - Hạnh phúc"
    ws.merge_cells('A4:N4')
    ws['A4'] = f"BẢNG LỊCH TRỰC KHOA {department.upper() if department else ''}"
    ws.merge_cells('A5:N5')
    ws['A5'] = f"Lịch trực tuần ngày {start.strftime('%d/%m/%Y')} đến ngày {end.strftime('%d/%m/%Y')}"

    # --- Dòng tiêu đề bảng bắt đầu từ dòng 7 ---
    start_row = 7
    header = ['Họ tên', 'Chức danh', 'Khoa'] + [d.strftime('%d/%m') for d in date_range]
    ws.append(header)

    # Dữ liệu từng người
    for u in schedule_data.values():
        row = [u['name'], u['position'], u['department']]
        for d in date_range:
            row.append(u['shifts'].get(d, ''))  # Nếu không có ca → để trống
        ws.append(row)

    # --- Chân trang ---
    last_row = ws.max_row + 2
    ws[f'A{last_row}'] = "Nơi nhận:"
    ws[f'A{last_row+1}'] = "- Ban Giám đốc"
    ws[f'A{last_row+2}'] = "- Các khoa/phòng"
    ws[f'A{last_row+3}'] = "- Đăng website"
    ws[f'A{last_row+4}'] = "- Lưu: VP, KH-CNTT"

    ws.merge_cells(start_row=last_row, start_column=5, end_row=last_row, end_column=7)
    ws.cell(row=last_row, column=5).value = "Người lập bảng"
    ws.merge_cells(start_row=last_row, start_column=10, end_row=last_row, end_column=12)
    ws.cell(row=last_row, column=10).value = "GIÁM ĐỐC"

    ws.cell(row=last_row+1, column=5).value = "(Ký, ghi rõ họ tên)"
    ws.cell(row=last_row+1, column=10).value = "(Ký, ghi rõ họ tên)"

    # --- Xuất file ---
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    return send_file(stream, as_attachment=True, download_name="lichtruc_dangngang.xlsx")

@app.route('/bang-cham-cong')
def bang_cham_cong():
    from datetime import datetime, timedelta, date
    from sqlalchemy import or_

    user_role = session.get('role')
    user_dept = session.get('department')

    today = datetime.today()
    start_date = request.args.get('start', today.replace(day=1).strftime('%Y-%m-%d'))
    end_date = request.args.get('end', today.strftime('%Y-%m-%d'))

    raw_department = request.args.get('department', '').strip()

    if user_role == 'admin':
        selected_department = raw_department if raw_department else None
        if selected_department:
            query = User.query.filter(User.department == selected_department)
        else:
            query = User.query  # không lọc theo khoa
    else:
        selected_department = user_dept
        query = User.query.filter(User.department == selected_department)


    selected_contract = request.args.get('contract_type', '')
    print_filter = request.args.get('print_filter') == 'yes'

    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    days_in_range = [start + timedelta(days=i) for i in range((end - start).days + 1)]


    if selected_contract:
        if selected_contract.lower() == "hợp đồng":
            query = query.filter(or_(
                User.contract_type.ilike("hợp đồng%"),
                User.contract_type.ilike("%hợp đồng"),
                User.contract_type.ilike("%hợp đồng%")
            ))
        else:
            query = query.filter(User.contract_type.ilike(selected_contract))

    users = query.filter(User.role != 'admin').order_by(User.name).all()

    schedules = Schedule.query.join(Shift).filter(
        Schedule.user_id.in_([u.id for u in users]),
        Schedule.work_date.between(start, end)
    ).all()

    schedule_map = {}
    summary = {user.id: {'kl': 0, 'tg': 0, '100': 0, 'bhxh': 0} for user in users}
    used_keys = set()

    for s in schedules:
        key = (s.user_id, s.work_date)
        if key in used_keys:
            continue
        used_keys.add(key)

        code = s.shift.code.upper() if s.shift and s.shift.code else 'X'
        schedule_map[key] = code

        if code == "KL":
            summary[s.user_id]['kl'] += 1
        elif code in ["X", "XĐ", "XĐ16", "XĐ24", "XĐ2", "XĐ3", "XĐL16", "XĐL24"] or code.startswith("XĐ") or code.startswith("XĐL"):
            summary[s.user_id]['tg'] += 1
        elif code in ["/X", "/NT"]:
            summary[s.user_id]['tg'] += 0.5
            summary[s.user_id]['100'] += 0.5
        elif code in ["NB", "P", "H", "CT", "L", "NT", "PC", "NBL", "PT"]:
            summary[s.user_id]['100'] += 1
        elif code in ["Ô", "CÔ", "DS", "TS", "TN"]:
            summary[s.user_id]['bhxh'] += 1

    holidays = [
        date(2025, 1, 1),
        date(2025, 4, 30),
        date(2025, 5, 1),
        date(2025, 9, 2),
    ]

    if user_role == 'admin':
        departments = [d[0] for d in db.session.query(User.department).filter(User.department != None).distinct().all()]
    else:
        departments = [user_dept]

    now = datetime.today()
    month = start.month
    year = start.year

    return render_template("bang_cham_cong.html", 
                    users=users,
                    departments=departments,
                    days_in_month=days_in_range,
                    schedule_map=schedule_map,
                    summary=summary,
                    holidays=holidays,
                    selected_department=selected_department,
                    selected_contract=selected_contract,
                    start_date=start_date,
                    end_date=end_date,
                    month=month,
                    year=year,
                    now=now
    )

@app.template_filter('break_code')
def break_code(code):
    if code and len(code) > 2:
        return code[:2] + '\n' + code[2:]
    return code

from flask import request, send_file
from models import User, Schedule

@app.route('/export-cham-cong')
def export_cham_cong():
    from datetime import datetime, timedelta
    from io import BytesIO
    import openpyxl
    from flask import send_file, request
    from sqlalchemy import or_

    # Lấy và xử lý tham số
    start_str = request.args.get('start', '').strip()
    end_str = request.args.get('end', '').strip()
    raw_department = request.args.get('department', '').strip()
    selected_contract = request.args.get('contract_type', '').strip().lower()

    # Sửa lỗi department=None từ URL
    if raw_department.lower() == 'none':
        raw_department = ''

    # Sửa lỗi ValueError do khoảng trắng dư
    start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
    days = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    # Lọc nhân viên theo điều kiện
    query = User.query
    if raw_department:
        query = query.filter(User.department == raw_department)
    if selected_contract:
        if selected_contract == "hợp đồng":
            query = query.filter(or_(
                User.contract_type.ilike("hợp đồng%"),
                User.contract_type.ilike("%hợp đồng"),
                User.contract_type.ilike("%hợp đồng%")
            ))
        elif selected_contract == "biên chế":
            query = query.filter(User.contract_type.ilike("biên chế"))
    users = query.order_by(User.name).all()

    user_ids = [u.id for u in users]
    schedules = Schedule.query.join(Shift).filter(
        Schedule.user_id.in_(user_ids),
        Schedule.work_date.between(start_date, end_date)
    ).all()
    schedule_map = {(s.user_id, s.work_date): s.shift.code for s in schedules if s.shift and s.shift.code}

    def count_summary(uid):
        vals = [schedule_map.get((uid, d), '') for d in days]
        return {
            'kl': vals.count('KL'),
            'tg': sum(1 for c in vals if c in ["X", "XĐ", "XĐ16", "XĐ24", "XĐ2", "XĐ3", "XĐL16", "XĐL24"] or c.startswith("XĐ")),
            '100': sum(1 for c in vals if c in ["NB", "P", "H", "CT", "L", "NT", "PC", "NBL", "PT"]),
            'bhxh': sum(1 for c in vals if c in ["Ô", "CÔ", "DS", "TS", "TN"])
        }

    # Tạo file Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bảng chấm công"

    # Đầu trang
    ws.append(["BỆNH VIỆN NHI TỈNH GIA LAI"])
    ws.append(["PHÒNG TỔ CHỨC - HCQT"])
    ws.append(["CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"])
    ws.append(["Độc lập - Tự do - Hạnh phúc"])
    ws.append([""])
    ws.append([f"BẢNG CHẤM CÔNG THÁNG {start_date.month} NĂM {start_date.year}"])
    ws.append([f"Khoa/Phòng: {raw_department or 'TOÀN VIỆN'}"])
    ws.append([f"Loại hợp đồng: {selected_contract.upper() if selected_contract else 'TẤT CẢ'}"])
    ws.append([""])
    
    header1 = ['STT', 'Họ và tên', 'Chức danh'] + [d.strftime('%d') for d in days] + ['Số công không hưởng lương', 'Số công hưởng lương TG', 'Số công nghỉ việc 100%', 'Số công BHXH']
    header2 = ['', '', ''] + ['CN' if d.weekday() == 6 else f"T{d.weekday() + 1}" for d in days] + ['', '', '', '']
    ws.append(header1)
    ws.append(header2)

    for idx, u in enumerate(users, start=1):
        row = [idx, u.name, u.position]
        row += [schedule_map.get((u.id, d), '') for d in days]
        s = count_summary(u.id)
        row += [s['kl'], s['tg'], s['100'], s['bhxh']]
        ws.append(row)

    # Chân trang
    ws.append([])
    footer = ['Nơi nhận:', '', '', 'Người lập']
    if raw_department:
        footer.append("Trưởng khoa" if "khoa" in raw_department.lower() else "Trưởng phòng")
    else:
        footer.append("")
    footer += ["Phòng TC - HCQT", "Giám đốc"]
    ws.append(footer)

    # DEBUG LOG
    print("✔️ Tổng số nhân viên:", len(users))
    print("✔️ Tổng ca trực lấy được:", len(schedules))
    print("✔️ Số dòng schedule_map:", len(schedule_map))

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="bang_cham_cong.xlsx")

from flask import render_template, request, send_file
from datetime import datetime, timedelta
from models import User, Shift, Schedule
import openpyxl
from io import BytesIO

@app.route('/report-all')
def report_all():
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    if start_str and end_str:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    else:
        start_date = datetime.today().date()
        end_date = start_date + timedelta(days=6)

    schedules = Schedule.query.join(User).join(Shift).filter(
        Schedule.work_date.between(start_date, end_date),
        Schedule.shift_id != None,
        User.department != None
    ).order_by(User.department, Schedule.work_date).all()

    grouped = {}

    for s in schedules:
        shift_name = s.shift.name.strip().lower()

        # ✅ Chỉ lấy các ca thật sự là "trực", bỏ "làm ngày", "nghỉ phép",...
        if not shift_name.startswith('trực'):
            continue

        dept = s.user.department.strip() if s.user.department else 'Khác'
        key = s.work_date.strftime('%a %d/%m')
        position = s.user.position.strip() if s.user.position else ''
        name = s.user.name.strip()

        # ✅ Gắn chức vụ nếu tên chưa có sẵn
        display_name = name if name.startswith(position) else f"{position}. {name}" if position else name

        # ✅ Tên ca trực ngắn gọn
        if 'thường trú' in shift_name:
            ca_text = 'Trực thường trú'
        elif '24' in shift_name:
            ca_text = 'Trực 24h'
        elif '16' in shift_name:
            ca_text = 'Trực 16h'
        elif '8' in shift_name:
            ca_text = 'Trực 8h'
        else:
            ca_text = f"Trực {int(s.shift.duration)}h"

        line = f"{display_name} ({ca_text})"

        grouped.setdefault(dept, {})
        grouped[dept].setdefault(key, [])
        grouped[dept][key].append((position, line))

    # ✅ Sắp xếp từng ngày theo chức vụ
    grouped_by_dept = {
        dept: {
            day: sorted(entries, key=lambda x: x[0]) for day, entries in dept_data.items()
        }
        for dept, dept_data in grouped.items() if any(dept_data.values())
    }

    # ✅ Ban giám đốc đứng đầu, sau đó là các khoa còn lại
    def sort_priority(name):
        name = name.lower()
        if 'giám đốc' in name:
            return '1_' + name
        elif 'ban giám' in name:
            return '1_' + name
        elif 'khoa' in name:
            return '2_' + name
        else:
            return '3_' + name

    dept_ordered = sorted(grouped_by_dept.keys(), key=sort_priority)
    date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    return render_template(
        'report_all.html',
        grouped_by_dept=grouped_by_dept,
        dept_ordered=dept_ordered,
        date_range=date_range,
        start_date=start_date,
        end_date=end_date
    )

@app.route('/export-report-all')
def export_report_all():
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    if start_str and end_str:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    else:
        start_date = datetime.today().date()
        end_date = start_date + timedelta(days=6)

    schedules = Schedule.query.join(User).join(Shift) \
        .filter(Schedule.work_date.between(start_date, end_date)) \
        .order_by(Schedule.work_date).all()

    grouped = {}
    for s in schedules:
        dept = s.user.department or 'Khác'
        pos = s.user.position or ''
        key = (dept, pos)
        grouped.setdefault(key, {})
        day = s.work_date.strftime('%a %d/%m')
        grouped[key][day] = grouped[key].get(day, '') + f"{s.user.name} ({s.shift.name}); "

    date_range = [(start_date + timedelta(days=i)).strftime('%a %d/%m')
                  for i in range((end_date - start_date).days + 1)]

    wb = openpyxl.Workbook()
    ws = wb.active
    header = ['Khoa/Phòng', 'Chức danh'] + date_range
    ws.append(header)

    for (dept, pos), days in grouped.items():
        row = [dept, pos] + [days.get(d, '') for d in date_range]
        ws.append(row)

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return send_file(stream, as_attachment=True, download_name='lich_truc_toan_vien.xlsx')

from models.ca_config import CaConfiguration

from models.ca import Ca

@app.route('/cas', methods=['GET', 'POST'])
def manage_cas():
    if session.get('role') not in ['admin', 'manager']:
        return redirect('/')

    user_role = session.get('role')
    user_dept = session.get('department')

    if user_role == 'admin':
        departments = [d[0] for d in db.session.query(User.department).filter(User.department != None).distinct().all()]
        selected_department = request.args.get('department') or request.form.get('department') or (departments[0] if departments else None)
    else:
        departments = [user_dept]
        selected_department = user_dept

    if request.method == 'POST':
        new_ca = Ca(
            name=request.form.get('ca_name'),
            department=selected_department,
            doctor_id=request.form.get('doctor_id'),
            nurse1_id=request.form.get('nurse1_id'),
            nurse2_id=request.form.get('nurse2_id'),
        )
        db.session.add(new_ca)
        db.session.commit()
        return redirect(f"/cas?department={selected_department}")

    doctors = User.query.filter(User.position == 'BS', User.department == selected_department).all()
    nurses = User.query.filter(User.position == 'ĐD', User.department == selected_department).all()
    cas = Ca.query.filter_by(department=selected_department).all()

    return render_template('cas.html',
                           departments=departments,
                           selected_department=selected_department,
                           doctors=doctors,
                           nurses=nurses,
                           cas=cas)

@app.route('/cas/delete/<int:ca_id>', methods=['POST'])
def delete_ca(ca_id):
    if session.get('role') not in ['admin', 'manager']:
        return "Không có quyền."
    ca = Ca.query.get_or_404(ca_id)
    db.session.delete(ca)
    db.session.commit()
    return redirect(request.referrer or '/cas')


@app.route('/cas/edit/<int:ca_id>', methods=['GET', 'POST'])
def edit_ca(ca_id):
    if session.get('role') not in ['admin', 'manager']:
        return redirect('/')

    ca = Ca.query.get_or_404(ca_id)
    departments = [d[0] for d in db.session.query(User.department).filter(User.department != None).distinct().all()]
    doctors = User.query.filter_by(department=ca.department, position='BS').all()
    nurses = User.query.filter_by(department=ca.department, position='ĐD').all()

    if request.method == 'POST':
        ca.name = request.form.get('ca_name')
        ca.doctor_id = request.form.get('doctor_id')
        ca.nurse1_id = request.form.get('nurse1_id')
        ca.nurse2_id = request.form.get('nurse2_id')
        db.session.commit()
        return redirect(f'/cas?department={ca.department}')

    return render_template('edit_ca.html', ca=ca, doctors=doctors, nurses=nurses, departments=departments)

from models.ca_config import CaConfiguration
from models.ca import Ca

@app.route('/generate-ca', methods=['GET', 'POST'])
def generate_ca_schedule_route():
    from models import Ca, Schedule, Shift, CaConfiguration, User

    selected_department = request.args.get('department') or request.form.get('department')
    model_type = request.form.get('model_type')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')

    # Lấy danh sách khoa có trong hệ thống
    departments = [d[0] for d in db.session.query(User.department).filter(User.department != None).distinct().all()]
    selected_config = None
    if selected_department:
        selected_config = CaConfiguration.query.filter_by(department=selected_department).first()

    # Nếu là POST và đủ dữ liệu thì tiến hành tạo lịch
    if request.method == 'POST' and selected_department and start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        days = (end_date - start_date).days + 1

        cas = Ca.query.filter_by(department=selected_department).all()
        shifts = Shift.query.all()

        if len(cas) < 3:
            flash("Phải có ít nhất 3 ca để chạy lịch 2 ca 3 kíp", "danger")
            return redirect(request.url)

        # Tạo mô hình 2 ca 3 kíp
        def pattern_2ca3kip(i):
            cycle = [
                [("Ca 1", "Làm ngày"), ("Trực Ca 2", "Trực đêm"), ("Ca 3", "Nghỉ")],
                [("Ca 3", "Làm ngày"), ("Trực Ca 1", "Trực đêm"), ("Ca 2", "Nghỉ")],
                [("Ca 2", "Làm ngày"), ("Trực Ca 3", "Trực đêm"), ("Ca 1", "Nghỉ")]
            ]
            return cycle[i % 3]

        assignments = []
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            day_shift_name, night_shift_name = pattern_2ca3kip(i)

            day_shift = next((s for s in shifts if s.name.lower() == day_shift_name[0].lower()), None)
            night_shift = next((s for s in shifts if s.name.lower() == night_shift_name[0].lower()), None)

            if not day_shift or not night_shift:
                continue

            ca_day = cas[i % len(cas)]
            ca_night = cas[(i + 1) % len(cas)]

            # Phân công ca ngày
            assignments.extend([
                Schedule(user_id=ca_day.doctor_id, shift_id=day_shift.id, work_date=current_date),
                Schedule(user_id=ca_day.nurse1_id, shift_id=day_shift.id, work_date=current_date),
                Schedule(user_id=ca_day.nurse2_id, shift_id=day_shift.id, work_date=current_date),
            ])

            # Phân công ca đêm
            assignments.extend([
                Schedule(user_id=ca_night.doctor_id, shift_id=night_shift.id, work_date=current_date),
                Schedule(user_id=ca_night.nurse1_id, shift_id=night_shift.id, work_date=current_date),
                Schedule(user_id=ca_night.nurse2_id, shift_id=night_shift.id, work_date=current_date),
            ])

        db.session.add_all(assignments)
        db.session.commit()

        flash("Tạo lịch trực 2 ca 3 kíp thành công", "success")
        return redirect(url_for('view_schedule', department=selected_department,
                                start_date=start_date_str, end_date=end_date_str))

    # GET hoặc POST thiếu thông tin -> hiển thị lại form
    return render_template(
        "generate_ca.html",
        department=selected_department,
        departments=departments,
        selected_config=selected_config,
        model_type=model_type,
        start_date=start_date_str,
        end_date=end_date_str
    )

@app.route('/configure-ca', methods=['GET', 'POST'])
def configure_ca():
    if session.get('role') not in ['admin', 'manager']:
        return "Bạn không có quyền truy cập."

    user_role = session.get('role')
    user_dept = session.get('department')

    if user_role == 'admin':
        departments = [d[0] for d in db.session.query(User.department).filter(User.department != None).distinct().all()]
    else:
        departments = [user_dept]

    selected_config = None
    message = None

    if request.method == 'POST':
        config_id = request.form.get('config_id')
        department = request.form['department']
        num_shifts = int(request.form['num_shifts'])
        cas_per_shift = int(request.form['cas_per_shift'])
        doctors_per_ca = int(request.form['doctors_per_ca'])
        nurses_per_ca = int(request.form['nurses_per_ca'])

        if config_id:
            config = CaConfiguration.query.get(int(config_id))
            if config:
                config.num_shifts = num_shifts
                config.cas_per_shift = cas_per_shift
                config.doctors_per_ca = doctors_per_ca
                config.nurses_per_ca = nurses_per_ca
                message = "Cập nhật cấu hình thành công."
        else:
            config = CaConfiguration(
                department=department,
                num_shifts=num_shifts,
                cas_per_shift=cas_per_shift,
                doctors_per_ca=doctors_per_ca,
                nurses_per_ca=nurses_per_ca
            )
            db.session.add(config)
            message = "Đã lưu cấu hình mới."

        db.session.commit()

    edit_id = request.args.get('edit_id')
    if edit_id:
        selected_config = CaConfiguration.query.get(int(edit_id))

    configs = CaConfiguration.query.all()
    return render_template(
        'configure_ca.html',
        departments=departments,
        configs=configs,
        selected_config=selected_config,
        message=message
    )

@app.route('/configure-ca/edit/<int:id>', methods=['GET', 'POST'])
def edit_ca_config(id):
    if session.get('role') not in ['admin', 'manager']:
        return redirect('/')
        
    config = CaConfiguration.query.get_or_404(id)
    departments = [d[0] for d in db.session.query(User.department).filter(User.department != None).distinct().all()]

    if request.method == 'POST':
        config.department = request.form['department']
        config.num_shifts = int(request.form['num_shifts'])
        config.cas_per_shift = int(request.form['cas_per_shift'])
        config.doctors_per_ca = int(request.form['doctors_per_ca'])
        config.nurses_per_ca = int(request.form['nurses_per_ca'])
        db.session.commit()
        return redirect('/configure-ca')

    return render_template('edit_ca_config.html', config=config, departments=departments)

@app.route('/delete-ca-config/<int:config_id>', methods=['POST'])
def delete_ca_config(config_id):
    if session.get('role') not in ['admin', 'manager']:
        return "Không có quyền."

    config = CaConfiguration.query.get(config_id)
    if config:
        db.session.delete(config)
        db.session.commit()
        flash("Đã xoá cấu hình.")

    return redirect('/configure-ca')

from models.ca_config import CaConfiguration

@app.route('/clinic-rooms')
def clinic_rooms():
    rooms = ClinicRoom.query.all()
    return render_template('clinic_rooms.html', rooms=rooms)

@app.route('/clinic-rooms/add', methods=['POST'])
def add_clinic_room():
    name = request.form['name']
    description = request.form.get('description')
    db.session.add(ClinicRoom(name=name, description=description))
    db.session.commit()
    return redirect('/clinic-rooms')

@app.route('/clinic-rooms/delete/<int:room_id>')
def delete_clinic_room(room_id):
    room = ClinicRoom.query.get(room_id)
    db.session.delete(room)
    db.session.commit()
    return redirect('/clinic-rooms')

@app.route('/clinic-rooms/update/<int:room_id>', methods=['POST'])
def update_clinic_room(room_id):
    room = ClinicRoom.query.get(room_id)
    room.name = request.form['name']
    room.description = request.form.get('description')
    db.session.commit()
    return redirect('/clinic-rooms')

from collections import defaultdict

from flask import send_file, request
from openpyxl.styles import Alignment, Font
from io import BytesIO
from collections import defaultdict
from datetime import datetime, timedelta
from models import User, Shift, Schedule, ClinicRoom  # Đảm bảo bạn có các model này
import re  # <== DÒNG CẦN THÊM

@app.route('/export-clinic-schedule')
def export_clinic_schedule():
    # Bước 1: Nhận tham số ngày
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    if not start_str or not end_str:
        return "Thiếu thông tin ngày", 400

    start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    # Bước 2: Lấy dữ liệu từ database
    rooms = ClinicRoom.query.all()
    schedules = Schedule.query.join(User).join(Shift).filter(Schedule.work_date.between(start_date, end_date)).all()

    # Bước 3: Tổ chức dữ liệu lịch trực
    clinic_schedule = {room.name: defaultdict(str) for room in rooms}
    user_positions = {}

    for s in schedules:
        user = s.user
        user_positions[user.name] = user.position
        shift_key = s.shift.name.lower().replace(" ", "")
        for room in rooms:
            room_key = room.name.lower().replace(" ", "")
            if room_key in shift_key:
                clinic_schedule[room.name][s.work_date] += f"{user.name}\n"
                break

    # Bước 4: Tạo file Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lịch phòng khám"

    # Dòng tiêu đề
    ws.cell(row=1, column=1, value="Phòng Khám")
    for col, d in enumerate(date_range, start=2):
        ws.cell(row=1, column=col, value=d.strftime('%a %d/%m'))

    # Nội dung từng phòng
    for row_idx, (room, shifts) in enumerate(clinic_schedule.items(), start=2):
        ws.cell(row=row_idx, column=1, value=room)
        for col_idx, d in enumerate(date_range, start=2):
            raw = shifts[d].strip()
            formatted = []
            for name in raw.split("\n"):
                pos = user_positions.get(name, "").lower()
                prefix = "BS." if "bs" in pos or "bác" in pos else "ĐD." if "đd" in pos or "điều" in pos else ""
                if name.strip():
                    formatted.append(f"{prefix} {name.strip()}")
            value = "\n".join(formatted)
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    # Căn giữa dòng tiêu đề
    for col in ws[1]:
        col.alignment = Alignment(horizontal="center", vertical="center")
        col.font = Font(bold=True)

    # Xuất file
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="lich_phong_kham.xlsx")

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect('/login')

    user = db.session.get(User, session['user_id'])  # ✅ Dòng này đã cập 

    if request.method == 'POST':
        current_pw = request.form['current_password']
        new_pw = request.form['new_password']
        confirm_pw = request.form['confirm_password']

        if current_pw != user.password:
            flash("❌ Mật khẩu hiện tại không đúng.", "danger")
        elif new_pw != confirm_pw:
            flash("❌ Mật khẩu mới không khớp.", "danger")
        else:
            user.password = new_pw
            db.session.commit()
            flash("✅ Đổi mật khẩu thành công.", "success")
            return redirect('/')

    return render_template('change_password.html', user=user)

import re
from datetime import datetime, timedelta
from collections import defaultdict
from flask import render_template, request


@app.route('/print-clinic-schedule')
def print_clinic_schedule():
    from collections import defaultdict

    start_str = request.args.get('start')
    end_str = request.args.get('end')
    if not start_str or not end_str:
        return "Thiếu thông tin ngày bắt đầu hoặc kết thúc.", 400

    start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    # Lấy danh sách phòng khám
    all_rooms = ClinicRoom.query.all()
    rooms_dict = {room.name.lower(): room.name for room in all_rooms if "tiếp đón" not in room.name.lower()}

    # Khởi tạo dữ liệu lịch (dùng key 'phong_kham' viết thường)
    clinic_schedule = {
        "tiep_don": defaultdict(list),
        "phong_kham": {name: defaultdict(list) for name in rooms_dict.values()}
    }

    # Lấy dữ liệu phân công
    schedules = Schedule.query.join(User).join(Shift).filter(
        Schedule.work_date.between(start_date, end_date),
        Shift.name.ilike('%phòng khám%') | Shift.name.ilike('%tiếp đón%')
    ).all()

    # Tạo bảng chức vụ người dùng
    user_positions = {}
    for s in schedules:
        name = s.user.name
        user_positions[name] = s.user.position or ""
        date = s.work_date
        shift_name = s.shift.name.lower()

        if "tiếp đón" in shift_name:
            clinic_schedule["tiep_don"][date].append(name)
        else:
            for room_key in rooms_dict:
                if room_key in shift_name:
                    room_name = rooms_dict[room_key]
                    clinic_schedule["phong_kham"][room_name][date].append(name)
                    break

    # 1. Loại bỏ phòng trống
    clinic_schedule["phong_kham"] = {
        name: day_dict for name, day_dict in clinic_schedule["phong_kham"].items()
        if any(day_dict[d] for d in date_range)
    }

    # 2. Sắp xếp phòng theo thứ tự chuẩn
    desired_order = [
        "phòng khám 1", "phòng khám 2", "phòng khám 3",
        "phòng khám ngoại", "phòng khám tmh", "phòng khám rhm",
        "phòng khám mắt", "phòng khám 8 (tc)", "phòng khám 9 (tc)"
    ]
    ordered_schedule = {}
    for name in desired_order:
        original_name = rooms_dict.get(name)
        if original_name in clinic_schedule["phong_kham"]:
            ordered_schedule[original_name] = clinic_schedule["phong_kham"][original_name]
    clinic_schedule["phong_kham"] = ordered_schedule

    # Tạo danh sách rooms từ lịch đã sắp xếp
    rooms = list(clinic_schedule["phong_kham"].keys())

    return render_template(
        'print-clinic-schedule.html',
        start_date=start_date,
        end_date=end_date,
        date_range=date_range,
        clinic_schedule=clinic_schedule,
        user_positions=user_positions,
        rooms=rooms,
        now=datetime.now(),
        get_titled_names=get_titled_names
    )

# Các route như /print-clinic-schedule ở trên...

# === Cuối file hoặc phần helper ===
def get_titled_names(raw_names, user_positions):
    result = []
    for name in raw_names.split("\n"):
        name = name.strip()
        if name:
            role = user_positions.get(name)
            prefix = ""
            if role == "BS":
                prefix = "BS. "
            elif role == "ĐD":
                prefix = "ĐD. "
            result.append(f"{prefix}{name}")
    return "<br>".join(result)

@app.route('/print-clinic-dept-schedule')
def print_clinic_dept_schedule():
    from collections import defaultdict
    import re

    start_str = request.args.get('start')
    end_str = request.args.get('end')
    if not start_str or not end_str:
        return "Thiếu thông tin ngày bắt đầu hoặc kết thúc.", 400

    start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    # Lấy danh sách phòng khám
    all_rooms = ClinicRoom.query.all()
    rooms_dict = {room.name.lower(): room.name for room in all_rooms if "tiếp đón" not in room.name.lower()}

    # Khởi tạo dữ liệu lịch (dùng key 'phong_kham' viết thường)
    clinic_schedule = {
        "tiep_don": defaultdict(list),
        "phong_kham": {name: defaultdict(list) for name in rooms_dict.values()}
    }

    # Lấy dữ liệu phân công
    schedules = Schedule.query.join(User).join(Shift).filter(
        Schedule.work_date.between(start_date, end_date),
        Shift.name.ilike('%phòng khám%') | Shift.name.ilike('%tiếp đón%')
    ).all()

    # Tạo bảng chức vụ người dùng
    user_positions = {}
    for s in schedules:
        name = s.user.name
        user_positions[name] = s.user.position or ""
        date = s.work_date
        shift_name = s.shift.name.lower()

        if "tiếp đón" in shift_name:
            clinic_schedule["tiep_don"][date].append(name)
        else:
            for room_key in rooms_dict:
                if room_key in shift_name:
                    room_name = rooms_dict[room_key]
                    clinic_schedule["phong_kham"][room_name][date].append(name)
                    break

    # 1. Loại bỏ phòng trống
    clinic_schedule["phong_kham"] = {
        name: day_dict for name, day_dict in clinic_schedule["phong_kham"].items()
        if any(day_dict[d] for d in date_range)
    }

    # 2. Sắp xếp phòng theo thứ tự chuẩn
    desired_order = [
        "phòng khám 1", "phòng khám 2", "phòng khám 3",
        "phòng khám ngoại", "phòng khám tmh", "phòng khám rhm",
        "phòng khám mắt", "phòng khám 8 (tc)", "phòng khám 9 (tc)"
    ]
    ordered_schedule = {}
    for name in desired_order:
        original_name = rooms_dict.get(name)
        if original_name in clinic_schedule["phong_kham"]:
            ordered_schedule[original_name] = clinic_schedule["phong_kham"][original_name]
    clinic_schedule["phong_kham"] = ordered_schedule

    # Tạo danh sách rooms từ lịch đã sắp xếp
    rooms = list(clinic_schedule["phong_kham"].keys())

    return render_template(
        'print-clinic-dept-schedule.html',
        start_date=start_date,
        end_date=end_date,
        date_range=date_range,
        clinic_schedule=clinic_schedule,
        user_positions=user_positions,
        rooms=rooms,
        now=datetime.now(),
        get_titled_names=get_titled_names
    )

def get_titled_names(name_input, user_positions):
    # Nếu đầu vào là chuỗi, chuyển sang danh sách
    if isinstance(name_input, str):
        names = [n.strip() for n in name_input.split(',') if n.strip()]
    elif isinstance(name_input, list):
        names = [n.strip() for n in name_input if n.strip()]
    else:
        return ''

    titled = []
    for name in names:
        title = user_positions.get(name, '').strip().upper()
        if title:
            titled.append(f"{title}. {name}")
        else:
            titled.append(name)

    return '<br>'.join(titled)

# Đăng ký vào template
@app.context_processor
def inject_helpers():
    return dict(get_titled_names=get_titled_names)

@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    return dict(user=user)

from flask import render_template, request, redirect
from models.shift_rate_config import ShiftRateConfig

@app.route('/shift-rate-config', methods=['GET', 'POST'])
def shift_rate_config():
    if session.get('role') != 'admin':
        return "Chỉ admin mới được phép truy cập."

    if request.method == 'POST':
        ca_loai = request.form['ca_loai']
        truc_loai = request.form['truc_loai']
        ngay_loai = request.form['ngay_loai']
        don_gia = int(request.form['don_gia'])
        new_rate = ShiftRateConfig(ca_loai=ca_loai, truc_loai=truc_loai, ngay_loai=ngay_loai, don_gia=don_gia)
        db.session.add(new_rate)
        db.session.commit()
        return redirect('/shift-rate-config')

    rates = ShiftRateConfig.query.all()
    return render_template('shift_rate_config.html', rates=rates)

@app.route('/shift-rate-config/delete/<int:rate_id>')
def delete_shift_rate(rate_id):
    if session.get('role') != 'admin':
        return "Không có quyền"
    rate = ShiftRateConfig.query.get_or_404(rate_id)
    db.session.delete(rate)
    db.session.commit()
    return redirect('/shift-rate-config')

from models.hscc_department import HSCCDepartment  # Import đầu file

@app.route('/configure-hscc', methods=['GET', 'POST'])
def configure_hscc():
    if session.get('role') != 'admin':
        return "Chỉ admin được phép truy cập."

    if request.method == 'POST':
        new_dept = request.form.get('department').strip()
        if new_dept and not HSCCDepartment.query.filter_by(department_name=new_dept).first():
            hscc = HSCCDepartment(department_name=new_dept)
            db.session.add(hscc)
            db.session.commit()
    departments = HSCCDepartment.query.all()
    return render_template('configure_hscc.html', departments=departments)

def classify_day(date):
    if date.weekday() >= 5:  # Thứ 7, Chủ nhật
        return "ngày_nghỉ"
    elif date.day in [1, 30, 31] or date.month in [1]:  # Giả định ngày lễ đơn giản
        return "ngày_lễ"
    else:
        return "ngày_thường"

@app.route('/shift-payment-view')
def shift_payment_view():
    user_role = session.get('role')
    user_dept = session.get('department')

    from calendar import month_name
    from collections import defaultdict

    def classify_day(date):
        ngay_le = {'01-01', '04-30', '05-01', '09-02'}
        mmdd = date.strftime('%m-%d')
        weekday = date.weekday()
        if mmdd in ngay_le:
            return 'ngày_lễ'
        elif weekday >= 5:
            return 'ngày_nghỉ'
        else:
            return 'ngày_thường'
        
    ca_chon = request.args.get('mode', '16h')
    selected_department = request.args.get('department', 'all')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # ✅ Nếu chưa có start/end thì tự động dùng tháng hiện tại
    if not start_date or not end_date:
        today = datetime.today()
        start_date_dt = today.replace(day=1)
        next_month = today.replace(day=28) + timedelta(days=4)
        last_day = (next_month - timedelta(days=next_month.day)).day
        end_date_dt = today.replace(day=last_day)
        start_date = start_date_dt.strftime('%Y-%m-%d')
        end_date = end_date_dt.strftime('%Y-%m-%d')
    else:
        start_date_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

    if user_role == 'admin':
        departments = [d[0] for d in db.session.query(User.department).distinct() if d[0]]
    else:
        departments = [user_dept]
        selected_department = user_dept  # ép luôn chọn khoa mình

    hscc_depts = [d.department_name for d in HSCCDepartment.query.all()]
    rates = {(r.ca_loai, r.truc_loai, r.ngay_loai): r.don_gia for r in ShiftRateConfig.query.all()}

    query = (
        Schedule.query
        .join(User).join(Shift)
        .filter(Schedule.work_date >= start_date_dt, Schedule.work_date <= end_date_dt)
        .filter(Shift.duration == (16 if ca_chon == '16h' else 24))
    )
    if selected_department != 'all':
        query = query.filter(User.department == selected_department)

    schedules = query.all()

    data = defaultdict(lambda: defaultdict(int))
    for s in schedules:
        user = s.user
        shift = s.shift

        # ❌ Bỏ qua ca trực thường trú
        if "thường trú" in shift.name.strip().lower():
            continue

        ngay_loai = classify_day(s.work_date)
        truc_loai = "HSCC" if user.department in hscc_depts else "thường"
        key = (truc_loai, ngay_loai)
        data[user][key] += 1

    rows = []
    co_ngay_le = False
    for user, info in data.items():
        if user.role == 'admin':
            continue  # ❌ Bỏ qua admin

        row = {
            'user': user,
            'tong_ngay': sum(info.values()),
            'tien_ca': 0,
            'tien_an': sum(info.values()) * 15000,
            'tong_tien': 0,
            'is_contract': user.contract_type == "Hợp đồng",
            'detail': {}
        }

        for key in [
            ("thường", "ngày_thường"), ("HSCC", "ngày_thường"),
            ("thường", "ngày_nghỉ"), ("HSCC", "ngày_nghỉ"),
            ("thường", "ngày_lễ"), ("HSCC", "ngày_lễ")
        ]:
            so_ngay = info.get(key, 0)
            if key[1] == 'ngày_lễ' and so_ngay > 0:
                co_ngay_le = True
            don_gia = rates.get((ca_chon, *key), 0)
            row['detail'][key] = {'so_ngay': so_ngay, 'don_gia': don_gia}
            row['tien_ca'] += so_ngay * don_gia

        row['tong_tien'] = row['tien_ca'] + row['tien_an']
        rows.append(row)

    thang = start_date_dt.month
    nam = start_date_dt.year

    return render_template(
        "shift_payment_view.html",
        ca_chon=ca_chon,
        rows=rows,
        departments=departments,
        selected_department=selected_department,
        mode=ca_chon,
        start_date=start_date,
        end_date=end_date,
        thang=thang,
        nam=nam,
        co_ngay_le=co_ngay_le
    )

@app.route('/tong-hop-cong-truc-view')
@login_required
def tong_hop_cong_truc_view():
    from collections import defaultdict
    from models.user import User
    from models.schedule import Schedule
    from models.shift import Shift

    user_role = session.get('role')
    user_dept = session.get('department')

    selected_department = request.args.get('department', '')
    if user_role == 'admin':
        departments = [d[0] for d in db.session.query(User.department).distinct() if d[0]]
    else:
        departments = [user_dept]

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    mode = request.args.get('mode', '16h')  # '16h' hoặc '24h'

    today = datetime.now()
    try:
        thang = int(start_date.split('-')[1])
        nam = int(start_date.split('-')[0])
    except:
        thang = today.month
        nam = today.year

    query = Schedule.query.join(User).join(Shift).filter(Schedule.work_date.between(start_date, end_date))

    if selected_department and selected_department != 'all':
        query = query.filter(User.department.ilike(selected_department))

    schedules = query.all()

    result_by_user = defaultdict(lambda: defaultdict(lambda: {'so_ngay': 0}))
    summary = defaultdict(int)

    for s in schedules:
        if not s.shift or not s.user:
            continue

        shift_name = s.shift.name.strip().lower()

        # ➖ Bỏ qua ca Trực thường trú
        if 'thường trú' in shift_name:
            continue

        # ⚠️ Bỏ qua ca không tính công trực
        if shift_name in ['nghỉ trực', 'nghỉ phép', 'làm ngày', 'làm 1/2 ngày', 'làm 1/2 ngày c']:
            continue

        # Áp dụng theo chế độ
        if mode == '24h' and '24h' not in shift_name:
            continue
        if mode == '16h' and '24h' in shift_name:
            continue

        # Phân loại ca
        if any(x in shift_name for x in ['hscc', 'cấp cứu', 'cc']):
            loai_ca = 'HSCC'
        else:
            loai_ca = 'thường'

        # Phân loại ngày
        mmdd = s.work_date.strftime('%m-%d')
        weekday = s.work_date.weekday()

        if mmdd in ['01-01', '04-30', '05-01', '09-02']:
            loai_ngay = 'ngày_lễ'
        elif weekday >= 5:
            loai_ngay = 'ngày_nghỉ'
        else:
            loai_ngay = 'ngày_thường'

        result_by_user[s.user_id][(loai_ca, loai_ngay)]['so_ngay'] += 1
        summary[(loai_ca, loai_ngay)] += 1

    user_ids = list(result_by_user.keys())
    users = User.query.filter(User.id.in_(user_ids), User.role != 'admin').all() if user_ids else []

    rows = []
    for user in users:
        detail = result_by_user[user.id]
        rows.append({
            'user': user,
            'detail': detail,
            'tong_ngay': sum([v['so_ngay'] for v in detail.values()]),
            'ghi_chu': ''
        })

    sum_row = {
        'detail': summary,
        'tong_ngay': sum(summary.values())
    }

    return render_template('tong_hop_cong_truc_view.html',
                           rows=rows,
                           sum_row=sum_row,
                           departments=departments,
                           selected_department=selected_department,
                           start_date=start_date,
                           end_date=end_date,
                           default_start=start_date,
                           default_end=end_date,
                           thang=thang,
                           nam=nam,
                           mode=mode)

@app.route('/tong-hop-cong-truc-print')
@login_required
def tong_hop_cong_truc_print():
    from collections import defaultdict
    from models.user import User
    from models.schedule import Schedule
    from models.shift import Shift

    selected_department = request.args.get('department', '')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    mode = request.args.get('mode', '16h')

    today = datetime.now()
    try:
        thang = int(start_date.split('-')[1])
        nam = int(start_date.split('-')[0])
    except:
        thang = today.month
        nam = today.year

    query = Schedule.query.join(User).join(Shift).filter(Schedule.work_date.between(start_date, end_date))
    if selected_department and selected_department != 'all':
        query = query.filter(User.department.ilike(selected_department))

    schedules = query.all()

    result_by_user = defaultdict(lambda: defaultdict(lambda: {'so_ngay': 0}))
    summary = defaultdict(int)

    for s in schedules:
        if not s.shift or not s.user:
            continue

        shift_name = s.shift.name.strip().lower()

        # ❌ Bỏ ca trực thường trú
        if 'thường trú' in shift_name:
            continue

        # ❌ Bỏ các ca không tính công trực
        if shift_name in ['nghỉ trực', 'nghỉ phép', 'làm ngày', 'làm 1/2 ngày', 'làm 1/2 ngày c']:
            continue

        if mode == '24h' and '24h' not in shift_name:
            continue
        if mode == '16h' and '24h' in shift_name:
            continue

        loai_ca = 'HSCC' if any(x in shift_name for x in ['hscc', 'cấp cứu', 'cc']) else 'thường'
        weekday = s.work_date.weekday()
        mmdd = s.work_date.strftime('%m-%d')

        if mmdd in ['01-01', '04-30', '05-01', '09-02']:
            loai_ngay = 'ngày_lễ'
        elif weekday >= 5:
            loai_ngay = 'ngày_nghỉ'
        else:
            loai_ngay = 'ngày_thường'

        result_by_user[s.user_id][(loai_ca, loai_ngay)]['so_ngay'] += 1
        summary[(loai_ca, loai_ngay)] += 1

    user_ids = list(result_by_user.keys())
    users = User.query.filter(User.id.in_(user_ids)).all() if user_ids else []

    rows = []
    for user in users:
        detail = result_by_user[user.id]
        rows.append({
            'user': user,
            'detail': detail,
            'tong_ngay': sum([v['so_ngay'] for v in detail.values()]),
            'ghi_chu': ''
        })

    sum_row = {
        'detail': summary,
        'tong_ngay': sum(summary.values())
    }

    return render_template('tong_hop_cong_truc.html',
        rows=rows,
        sum_row=sum_row,
        selected_department=selected_department,
        start_date=start_date,
        current_day=today.day,
        current_month=today.month,
        current_year=today.year,
        thang=thang,
        nam=nam,
        mode=mode
    )

@app.route('/export-shift-payment-all')
def export_shift_payment_all():
    from calendar import month_name
    from openpyxl.styles import Font, Alignment, Border, Side

    def classify_day(date):
        # Danh sách ngày lễ cố định (thêm nếu cần)
        ngay_le = {'01-01', '04-30', '05-01', '09-02'}
        mmdd = date.strftime('%m-%d')
        weekday = date.weekday()
        if mmdd in ngay_le:
            return 'ngày_lễ'
        elif weekday >= 5:
            return 'ngày_nghỉ'
        else:
            return 'ngày_thường'
        
    # 📥 Tham số lọc
    ca_chon = request.args.get('mode', '16h')
    selected_department = request.args.get('department', 'all')
    start_date = request.args.get('start_date', '2025-06-01')
    end_date = request.args.get('end_date', '2025-06-30')

    start_date_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    thang = start_date_dt.month
    nam = start_date_dt.year

    # 🔧 Dữ liệu
    hscc_depts = [d.department_name for d in HSCCDepartment.query.all()]
    rates = {(r.ca_loai, r.truc_loai, r.ngay_loai): r.don_gia for r in ShiftRateConfig.query.all()}

    query = (
        Schedule.query
        .join(User).join(Shift)
        .filter(Schedule.work_date >= start_date_dt, Schedule.work_date <= end_date_dt)
        .filter(Shift.duration == (16 if ca_chon == '16h' else 24))
    )
    if selected_department != 'all':
        query = query.filter(User.department == selected_department)

    schedules = query.all()

    # 📊 Gom dữ liệu
    data = defaultdict(lambda: defaultdict(int))
    for s in schedules:
        user = s.user
        ngay_loai = classify_day(s.work_date)
        truc_loai = "HSCC" if user.department in hscc_depts else "thường"
        key = (truc_loai, ngay_loai)
        data[user][key] += 1

    # 📄 Tạo Excel
    wb = Workbook()
    ws = wb.active
    ws.title = f"BẢNG TRỰC {ca_chon}"

    # 🎨 Định dạng chung
    bold = Font(bold=True)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                         top=Side(style='thin'), bottom=Side(style='thin'))

    # 📝 Tiêu đề đầu trang
    ws.merge_cells("A1:M1")
    ws["A1"] = "SỞ Y TẾ TỈNH GIA LAI"
    ws["A1"].font = bold

    ws.merge_cells("A2:M2")
    ws["A2"] = "BỆNH VIỆN NHI"
    ws["A2"].font = bold

    ws.merge_cells("A4:M4")
    ws["A4"] = f"BẢNG THANH TOÁN TIỀN TRỰC THÁNG {thang:02d} NĂM {nam}"
    ws["A4"].alignment = center
    ws["A4"].font = Font(bold=True, size=13)

    # 🧾 Tiêu đề bảng (gồm 2 dòng)
    ws.append([
        "STT", "HỌ TÊN",
        "Trực thường\n(Ngày thường)", "Trực HSCC\n(Ngày thường)",
        "Trực thường\n(Ngày nghỉ)", "Trực HSCC\n(Ngày nghỉ)",
        "Trực thường\n(Ngày lễ)", "Trực HSCC\n(Ngày lễ)",
        "Tổng số\nngày trực", "Tiền ca\n(QĐ 73)",
        "Tiền ăn\n(15k/ngày)", "Tổng cộng", "Ghi chú"
    ])
    for cell in ws[6]:
        cell.font = bold
        cell.alignment = center
        cell.border = thin_border

    # 📥 Ghi dữ liệu từng nhân viên
    for i, (user, info) in enumerate(data.items(), start=1):
        total_day = sum(info.values())
        tien_ca = 0

        row_data = [i, user.name]

        for key in [
            ("thường", "ngày_thường"), ("HSCC", "ngày_thường"),
            ("thường", "ngày_nghỉ"),   ("HSCC", "ngày_nghỉ"),
            ("thường", "ngày_lễ"),     ("HSCC", "ngày_lễ")
        ]:
            so_ngay = info.get(key, 0)
            don_gia = rates.get((ca_chon, *key), 0)
            row_data.append(so_ngay)
            tien_ca += so_ngay * don_gia

        tien_an = total_day * 15000
        tong_cong = tien_ca + tien_an

        row_data += [total_day, tien_ca, tien_an, tong_cong]
        row_data.append("HD" if user.contract_type == "Hợp đồng" else "")

        ws.append(row_data)
        for cell in ws[ws.max_row]:
            cell.alignment = center
            cell.border = thin_border

    # 📤 Xuất file
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    filename = f"BANG_THANH_TOAN_{thang:02d}_{nam}_{ca_chon}.xlsx"
    return send_file(stream, as_attachment=True, download_name=filename)

@app.route('/print-shift-payment')
def print_shift_payment():
    from calendar import month_name
    from collections import defaultdict
    from datetime import datetime

    def classify_day(date):
        # Danh sách ngày lễ cố định (thêm nếu cần)
        ngay_le = {'01-01', '04-30', '05-01', '09-02'}
        mmdd = date.strftime('%m-%d')
        weekday = date.weekday()
        if mmdd in ngay_le:
            return 'ngày_lễ'
        elif weekday >= 5:
            return 'ngày_nghỉ'
        else:
            return 'ngày_thường'
        
    ca_chon = request.args.get('mode', '16h')
    selected_department = request.args.get('department', 'all')
    start_date = request.args.get('start_date', '2025-06-01')
    end_date = request.args.get('end_date', '2025-06-30')

    start_date_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    thang = start_date_dt.month
    nam = start_date_dt.year

    # 👇 Thêm dòng này để lấy ngày in hiện tại
    today = datetime.now()
    current_day = today.day
    current_month = today.month
    current_year = today.year

    hscc_depts = [d.department_name for d in HSCCDepartment.query.all()]
    rates = {(r.ca_loai, r.truc_loai, r.ngay_loai): r.don_gia for r in ShiftRateConfig.query.all()}

    query = (
        Schedule.query
        .join(User).join(Shift)
        .filter(Schedule.work_date >= start_date_dt, Schedule.work_date <= end_date_dt)
        .filter(Shift.duration == (16 if ca_chon == '16h' else 24))
    )
    if selected_department != 'all':
        query = query.filter(User.department == selected_department)

    schedules = query.all()

    data = defaultdict(lambda: defaultdict(int))
    for s in schedules:
        user = s.user
        shift = s.shift
        # ✅ Bỏ qua ca "Trực thường trú"
        if "thường trú" in shift.name.strip().lower():
            continue

        ngay_loai = classify_day(s.work_date)
        truc_loai = "HSCC" if user.department in hscc_depts else "thường"
        key = (truc_loai, ngay_loai)
        data[user][key] += 1

    rows = []
    sum_row = {
        'tong_ngay': 0,
        'tien_ca': 0,
        'tien_an': 0,
        'tong_tien': 0,
        'detail': {
            ("thường", "ngày_thường"): 0,
            ("HSCC", "ngày_thường"): 0,
            ("thường", "ngày_nghỉ"): 0,
            ("HSCC", "ngày_nghỉ"): 0,
            ("thường", "ngày_lễ"): 0,
            ("HSCC", "ngày_lễ"): 0
        }
    }

    for user, info in data.items():
        row = {
            'user': user,
            'tong_ngay': sum(info.values()),
            'tien_ca': 0,
            'tien_an': sum(info.values()) * 15000,
            'tong_tien': 0,
            'is_contract': user.contract_type == "Hợp đồng",
            'ghi_chu': 'HĐ' if user.contract_type == 'Hợp đồng' else '',
            'detail': {}
        }

        for key in sum_row['detail'].keys():
            so_ngay = info.get(key, 0)
            don_gia = rates.get((ca_chon, *key), 0)
            row['detail'][key] = {'so_ngay': so_ngay, 'don_gia': don_gia}
            row['tien_ca'] += so_ngay * don_gia
            sum_row['detail'][key] += so_ngay

        row['tong_tien'] = row['tien_ca'] + row['tien_an']

        sum_row['tong_ngay'] += row['tong_ngay']
        sum_row['tien_ca'] += row['tien_ca']
        sum_row['tien_an'] += row['tien_an']
        sum_row['tong_tien'] += row['tong_tien']

        rows.append(row)

    return render_template(
        "shift_payment_print.html",
        ca_chon=ca_chon,
        rows=rows,
        sum_row=sum_row,
        selected_department=selected_department,
        mode=ca_chon,
        start_date=start_date,
        end_date=end_date,
        thang=thang,
        nam=nam,
        current_day=current_day,
        current_month=current_month,
        current_year=current_year,
        tong_tien_bang_chu=num2text(int(sum_row['tong_tien']))
    )

from utils import num2text

from utils.num2text import num2text  # ✅ chỉ lấy hàm, không lấy module
text = num2text(1530000)
# Kết quả: "Một triệu năm trăm ba mươi nghìn đồng"

from datetime import datetime  # Đảm bảo đã import ở đầu file

@app.route('/print-shift-payment-summary')
def print_shift_payment_summary():
    from collections import defaultdict

    def classify_day(date):
        # Danh sách ngày lễ cố định (thêm nếu cần)
        ngay_le = {'01-01', '04-30', '05-01', '09-02'}
        mmdd = date.strftime('%m-%d')
        weekday = date.weekday()
        if mmdd in ngay_le:
            return 'ngày_lễ'
        elif weekday >= 5:
            return 'ngày_nghỉ'
        else:
            return 'ngày_thường'
        
    def roman(num):
        roman_map = zip(
            (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1),
            ("M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I")
        )
        result = ''
        for i, r in roman_map:
            while num >= i:
                result += r
                num -= i
        return result

    ca_chon = request.args.get('mode', '16h')
    start_date = request.args.get('start_date', '2025-06-01')
    end_date = request.args.get('end_date', '2025-06-30')
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

    hscc_depts = [d.department_name for d in HSCCDepartment.query.all()]
    rates = {(r.ca_loai, r.truc_loai, r.ngay_loai): r.don_gia for r in ShiftRateConfig.query.all()}

    schedules = (
        Schedule.query.join(User).join(Shift)
        .filter(Schedule.work_date >= start_dt, Schedule.work_date <= end_dt)
        .filter(Shift.duration == (16 if ca_chon == '16h' else 24))
        .filter(~Shift.name.ilike('%thường trú%'))  # ❌ Loại bỏ ca thường trú
        .all()
    )

    grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    for s in schedules:
        user = s.user
        dept = user.department or 'Không rõ'
        key = ("HSCC" if dept in hscc_depts else "thường", classify_day(s.work_date))
        grouped[dept][user][key] += 1

    summary_rows = []
    total = defaultdict(int)

    for i, (dept, users) in enumerate(grouped.items(), start=1):
        summary_rows.append({
            'is_dept': True,
            'index_label': f"{roman(i)}.",
            'department': dept
        })

        for j, (user, counts) in enumerate(users.items(), start=1):
            row = {
                'is_dept': False,
                'index_label': str(j),
                'department': dept,
                'full_name': user.name,
                'is_contract': user.contract_type and 'hợp đồng' in user.contract_type.lower(),
                'thuong_thuong': 0,
                'hscc_thuong': 0,
                'thuong_nghi': 0,
                'hscc_nghi': 0,
                'thuong_le': 0,
                'hscc_le': 0,
                'total_shifts': 0,
                'tien_qd73': 0,
                'tien_an': 0,
                'tong_tien': 0
            }

            for key, so_ngay in counts.items():
                loai_truc, ngay_loai = key
                don_gia = rates.get((ca_chon, loai_truc, ngay_loai), 0)
                tien = so_ngay * don_gia

                if (loai_truc, ngay_loai) == ('thường', 'ngày_thường'):
                    row['thuong_thuong'] = so_ngay
                elif (loai_truc, ngay_loai) == ('HSCC', 'ngày_thường'):
                    row['hscc_thuong'] = so_ngay
                elif (loai_truc, ngay_loai) == ('thường', 'ngày_nghỉ'):
                    row['thuong_nghi'] = so_ngay
                elif (loai_truc, ngay_loai) == ('HSCC', 'ngày_nghỉ'):
                    row['hscc_nghi'] = so_ngay
                elif (loai_truc, ngay_loai) == ('thường', 'ngày_lễ'):
                    row['thuong_le'] = so_ngay
                elif (loai_truc, ngay_loai) == ('HSCC', 'ngày_lễ'):
                    row['hscc_le'] = so_ngay

                row['tien_qd73'] += tien
                row['total_shifts'] += so_ngay

            row['tien_an'] = row['total_shifts'] * 15000
            row['tong_tien'] = row['tien_qd73'] + row['tien_an']

            for k in ['thuong_thuong', 'hscc_thuong', 'thuong_nghi', 'hscc_nghi', 'thuong_le', 'hscc_le',
                      'total_shifts', 'tien_qd73', 'tien_an', 'tong_tien']:
                total[k] += row[k]

            summary_rows.append(row)

    now = datetime.now()  # ✅ Dùng thời điểm hiện tại để in

    return render_template(
        'shift_payment_summary_print.html',
        summary_rows=summary_rows,
        total_shifts=total['total_shifts'],
        total_qd73=total['tien_qd73'],
        total_an=total['tien_an'],
        total_sum=total['tong_tien'],
        sum_thuong_thuong=total['thuong_thuong'],
        sum_hscc_thuong=total['hscc_thuong'],
        sum_thuong_nghi=total['thuong_nghi'],
        sum_hscc_nghi=total['hscc_nghi'],
        sum_thuong_le=total['thuong_le'],
        sum_hscc_le=total['hscc_le'],
        tong_tien_bang_chu=num2text(int(total['tong_tien'])),
        thang=start_dt.month,
        nam=start_dt.year,
        now=now,  # ✅ Truyền `now` vào template
        mode=ca_chon
    )

@app.route('/configure-hscc/delete/<int:dept_id>', methods=['POST'])
def delete_hscc(dept_id):
    if session.get('role') != 'admin':
        return "Không có quyền."
    dept = HSCCDepartment.query.get_or_404(dept_id)
    db.session.delete(dept)
    db.session.commit()
    return redirect('/configure-hscc')

from models.user import User

from sqlalchemy import inspect

@app.route('/init-db')
def init_db():
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()

    # Chỉ tạo bảng nếu chưa tồn tại
    if 'user' not in existing_tables:
        db.create_all()
        return "✅ Đã tạo bảng vào PostgreSQL"
    return "⚠️ Bảng đã tồn tại, không tạo lại."


@app.route('/run-seed')
def run_seed():
    try:
        import seed
        return "✅ Đã chạy seed.py thành công!"
    except Exception as e:
        return f"❌ Lỗi khi chạy seed.py: {str(e)}"

import time

@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def log_request_time(response):
    duration = time.time() - request.start_time
    app.logger.info(f"[REQUEST TIME] {request.method} {request.path} - {duration:.3f}s")
    return response

@app.cli.command("db-upgrade")
def db_upgrade():
    from flask_migrate import upgrade
    upgrade()

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

import traceback

@app.errorhandler(Exception)
def handle_exception(e):
    return f"<h2>Internal Server Error</h2><pre>{traceback.format_exc()}</pre>", 500

if __name__ == '__main__':
    import os
    from sqlalchemy import inspect

    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        required_tables = {'user', 'permission'}

        # ✅ Tạo bảng nếu thiếu
        if not required_tables.issubset(set(existing_tables)):
            from models.permission import Permission
            from models.user import User
            db.create_all()
            print("✅ Đã tạo tất cả bảng cần thiết.")
        else:
            print("✅ Các bảng chính đã tồn tại.")

        # ✅ Thêm cột 'active' nếu chưa có
        with db.engine.connect() as connection:
            result = connection.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name='user' AND column_name='active';"
            )
            if not result.fetchone():
                connection.execute('ALTER TABLE "user" ADD COLUMN active BOOLEAN DEFAULT TRUE;')
                print("✅ Đã thêm cột 'active' vào bảng user.")
            else:
                print("✅ Cột 'active' đã tồn tại.")

        # ✅ Thêm admin nếu chưa có
        from models.user import User
        if not User.query.filter_by(username='admin').first():
            admin = User(
                name="Quản trị viên",
                username="admin",
                password="admin",
                role="admin",
                department="Phòng CNTT",
                position="Bác sĩ"
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Đã tạo tài khoản admin.")
        else:
            print("⚠️ Tài khoản admin đã tồn tại.")

    # ✅ Khởi động Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
 
