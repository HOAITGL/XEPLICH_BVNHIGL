from models.schedule_lock import ScheduleLock

from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


from flask import Flask, render_template, request, redirect, session, send_file, flash
from flask_login import login_required
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import ScheduleSignature
from models.ScheduleSignature import ScheduleSignature
from flask import Flask
from extensions import db  # Sử dụng đối tượng db đã khởi tạo trong extensions.py

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'lichtruc2025'

# Khởi tạo db và migrate
db.init_app(app)
migrate = Migrate(app, db)

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

login_manager = LoginManager()
login_manager.init_app(app)

from models.user import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import models
from models.user import User
from models.shift import Shift
from models.schedule import Schedule
from models.ca_config import CaConfiguration
from models.clinic_room import ClinicRoom
from models.ca import Ca

# Import logic
from scheduler.logic import generate_schedule

@app.before_request
def require_login():
    allowed_routes = ['login']
    if 'user_id' not in session and request.endpoint not in allowed_routes:
        return redirect('/login')

@app.context_processor
def inject_user():
    return {
        'user': {
            'role': session.get('role'),
            'department': session.get('department'),
            'name': session.get('name')  # <-- cần dòng này!
        }
    }

@app.route('/')
def index():
    return render_template('index.html')

from flask_login import login_user

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            # Gọi login_user từ Flask-Login
            login_user(user)

            # Gán session nếu cần sử dụng song song
            session['user_id'] = user.id
            session['role'] = user.role
            session['department'] = user.department

            flash("✅ Đăng nhập thành công.", "success")
            return redirect('/')
        else:
            flash("❌ Sai tài khoản hoặc mật khẩu. Vui lòng liên hệ admin.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/assign', methods=['GET', 'POST'])
def assign_schedule():
    from flask import flash
    from datetime import datetime, timedelta

    user_role = session.get('role')
    user_dept = session.get('department')

    if user_role != 'admin':
        departments = [user_dept]
    else:
        departments = [d[0] for d in db.session.query(User.department).filter(User.department != None).distinct().all()]

    selected_department = request.args.get('department') if request.method == 'GET' else request.form.get('department')
    users = User.query.filter_by(department=selected_department).all() if selected_department else []
    shifts = Shift.query.all()

    if request.method == 'POST':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        duplicated_entries = []

        for checkbox in request.form.getlist('schedule'):
            user_id, shift_id = checkbox.split('-')
            user_id = int(user_id)
            shift_id = int(shift_id)

            current = start_date
            while current <= end_date:
                existing = Schedule.query.filter_by(user_id=user_id, work_date=current).first()
                if existing:
                    duplicated_entries.append(f"{existing.user.name} đã có lịch ngày {current.strftime('%d/%m/%Y')}")
                else:
                    new_schedule = Schedule(user_id=user_id, shift_id=shift_id, work_date=current)
                    db.session.add(new_schedule)
                current += timedelta(days=1)

        db.session.commit()

        if duplicated_entries:
            for message in duplicated_entries:
                flash(f"⚠️ {message}", "danger")
        else:
            flash("✅ Đã lưu lịch thành công.", "success")

        return redirect('/assign?department=' + selected_department)

    return render_template('assign.html', departments=departments, selected_department=selected_department, users=users, shifts=shifts)

@app.route('/auto-assign')
def auto_assign_page():
    selected_department = request.args.get('department')

    departments = db.session.query(User.department).distinct().all()
    departments = [d[0] for d in departments if d[0]]

    users = User.query.filter_by(department=selected_department).all() if selected_department else []
    shifts = Shift.query.all()

    return render_template('auto_assign.html',
                           departments=departments,
                           selected_department=selected_department,
                           users=users,
                           shifts=shifts)

@app.route('/schedule', methods=['GET', 'POST'])
def view_schedule():
    selected_department = request.args.get('department')
    user_role = session.get('role')
    user_dept = session.get('department')

    # Giới hạn department nếu là manager/user
    if user_role in ['manager', 'user']:
        selected_department = user_dept

    # Lấy danh sách khoa
    if user_role == 'admin':
        departments = [d[0] for d in db.session.query(User.department)
                       .filter(User.department.isnot(None)).distinct().all()]
    else:
        departments = [user_dept]

    # Ngày bắt đầu và kết thúc
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    else:
        start_date = datetime.today().date()
        end_date = start_date + timedelta(days=6)

    # Truy vấn lịch
    query = Schedule.query.join(User).join(Shift)\
        .filter(Schedule.work_date.between(start_date, end_date))

    if selected_department:
        query = query.filter(User.department == selected_department)

    schedules = query.order_by(Schedule.work_date).all()
    date_range = sorted({s.work_date for s in schedules})

    # Tổ chức lại dữ liệu
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
        schedule_data[u.id]['shifts'][s.work_date] = s.shift.name
        schedule_data[u.id]['shifts_full'][s.work_date] = {
            'shift_id': s.shift.id,
            'shift_name': s.shift.name
        }

    # Lọc dữ liệu cần in
    filtered_for_print = {
        uid: data for uid, data in schedule_data.items()
        if any("trực" in s['shift_name'].lower() for s in data['shifts_full'].values())
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

    user = {
        'role': session.get('role'),
        'department': session.get('department'),
        'name': session.get('name')
    }

    # Truyền thông tin vào template
    return render_template(
        'schedule.html',
        departments=departments,
        selected_department=selected_department,
        schedule_data=schedule_data,
        print_data=filtered_for_print,
        date_range=date_range,
        start_date=start_date,
        end_date=end_date,
        now=datetime.now(),
        is_signed=is_signed,
        signed_at=signed_at,
        locked=locked,
        user={
            'role': session.get('role'),
            'department': session.get('department'),
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
        for s in schedules:
            new_shift_id = request.form.get(f'shift_{s.id}')
            if new_shift_id and int(new_shift_id) != s.shift_id:
                s.shift_id = int(new_shift_id)
        db.session.commit()
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

    if user_role in ['manager', 'user']:
        users = User.query.filter(User.department == user_dept).order_by(User.name).all()
        departments = [user_dept]
        selected_department = user_dept
    else:
        departments = [d[0] for d in db.session.query(User.department).filter(User.department != None).distinct().all()]
        selected_department = request.args.get('department')
        if selected_department:
            users = User.query.filter(User.department == selected_department).order_by(User.name).all()
        else:
            users = User.query.order_by(User.department, User.name).all()

    return render_template('users_by_department.html',
                           users=users,
                           departments=departments,
                           selected_department=selected_department)

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
    try:
        department = request.form.get('department')
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        user_ids = request.form.getlist('user_ids')
        shift_ids = request.form.getlist('shift_ids')

        if not user_ids or not shift_ids:
            flash("⚠️ Vui lòng chọn ít nhất 1 người và 1 ca trực.", "danger")
            return redirect(request.referrer)

        shift_id = int(shift_ids[0])  # chỉ dùng ca đầu tiên được chọn
        date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

        assignments = []
        conflicts = []

        user_ids = [int(uid) for uid in user_ids]
        user_count = len(user_ids)
        for idx, work_date in enumerate(date_range):
            uid = user_ids[idx % user_count]

            existing = Schedule.query.filter_by(user_id=uid, work_date=work_date).first()
            if existing:
                user = User.query.get(uid)
                conflicts.append(f"🔁 {user.name} đã có lịch ngày {work_date.strftime('%d/%m/%Y')}")
            else:
                assignments.append(Schedule(user_id=uid, shift_id=shift_id, work_date=work_date))

        if assignments:
            db.session.add_all(assignments)
            db.session.commit()
            flash("✅ Đã tạo lịch tự động theo tua thành công.", "success")

        for msg in conflicts:
            flash(msg, "danger")

        return redirect(url_for('generate_schedule_route'))

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Lỗi tạo lịch: {str(e)}", "danger")
        return redirect(request.referrer)

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
from app import db

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
        flash("✅ Đã thêm ca trực mới.", "success")
        return redirect('/shifts')

    return render_template('add_shift.html')

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
            return redirect('/shifts')

        except ValueError as ve:
            flash("⚠️ Vui lòng nhập giờ theo định dạng HH:MM hoặc HH:MM:SS", "danger")

    return render_template('edit_shift.html', shift=shift, old=old)

@app.route('/shifts/delete/<int:shift_id>')
def delete_shift(shift_id):
    shift = Shift.query.get_or_404(shift_id)
    db.session.delete(shift)
    db.session.commit()
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
def import_shifts():
    import openpyxl
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
                # Chuyển start và end thành đối tượng time nếu có thể
                def to_time(val):
                    if isinstance(val, time):
                        return val
                    if isinstance(val, datetime):
                        return val.time()
                    if isinstance(val, str):
                        try:
                            return datetime.strptime(val.strip(), '%H:%M').time()
                        except ValueError:
                            try:
                                return datetime.strptime(val.strip(), '%H:%M:%S').time()
                            except ValueError:
                                return None
                    return None

                start_time = to_time(start)
                end_time = to_time(end)

                if not start_time or not end_time:
                    flash(f"Dòng {idx}: Bạn đã nhập sai giờ bắt đầu hoặc giờ kết thúc. "
                          f"Vui lòng dùng định dạng giờ 'HH:MM' hoặc 'HH:MM:SS'.", "error")
                    continue

                existing = Shift.query.filter_by(code=code).first()
                if not existing:
                    new_shift = Shift(name=name, code=code, start_time=start_time, end_time=end_time, duration=duration)
                    db.session.add(new_shift)

        db.session.commit()
        flash("Đã nhập ca trực thành công.", "success")
    except Exception as e:
        flash(f"Đã xảy ra lỗi: {str(e)}", "error")

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
        user.email = request.form['email']
        db.session.commit()
        return redirect('/users-by-department')

    return render_template('edit_user.html', user=user)


@app.route('/users/add', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        department = request.form['department']
        position = request.form['position']
        contract_type = request.form.get('contract_type')
        phone = request.form.get('phone')
        email = request.form.get('email')

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
            email=email
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
                row = row[:9]  # Lấy đúng 9 cột
                if len(row) < 6:
                    continue

                name, username, password, role, department, position = row[:6]
                contract_type = row[6] if len(row) > 6 else None
                email         = row[7] if len(row) > 7 else None
                phone         = row[8] if len(row) > 8 else None

                if User.query.filter_by(username=username).first():
                    skipped_users.append(username)
                    continue

                user = User(
                    name=name,
                    username=username,
                    password=password,
                    role=role,
                    department=department,
                    position=position,
                    contract_type=contract_type,
                    email=email,
                    phone=phone
                )
                db.session.add(user)
                imported_count += 1

            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("❌ Lỗi khi lưu dữ liệu. Vui lòng kiểm tra file Excel.", "danger")
                return redirect('/users-by-department')

            # ✅ Gửi thông báo kết quả
            if skipped_users:
                flash(f"⚠️ Đã nhập {imported_count} người dùng. Các tài khoản bị bỏ qua do trùng tên đăng nhập: {', '.join(skipped_users)}", "warning")
            else:
                flash(f"✅ Đã nhập thành công {imported_count} người dùng.", "success")

            return redirect('/users-by-department')

        else:
            flash("❌ Vui lòng chọn file Excel định dạng .xlsx", "danger")
            return redirect('/import-users')

    return render_template('import_users.html')

@app.route('/roles', methods=['GET', 'POST'])
def manage_roles():
    if session.get('role') != 'admin':
        return "Bạn không có quyền truy cập trang này."

    users = User.query.order_by(User.department).all()

    if request.method == 'POST':
        for user in users:
            role = request.form.get(f'role_{user.id}')
            dept = request.form.get(f'department_{user.id}')
            if role and dept:
                user.role = role
                user.department = dept
        db.session.commit()
        return redirect('/roles')

    departments = [d[0] for d in db.session.query(User.department).distinct().all() if d[0]]
    roles = ['admin', 'manager', 'user']  # cập nhật quyền hệ thống
    positions = ['Bác sĩ', 'Điều dưỡng', 'Kỹ thuật viên']  # chức danh chuyên môn
    return render_template('manage_roles.html', users=users, departments=departments, roles=roles, positions=positions)

@app.route('/users/delete/<int:user_id>', methods=['POST', 'GET'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
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

from sqlalchemy import or_

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

    users = query.order_by(User.name).all()

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

from flask import send_file, request
from io import BytesIO
import openpyxl

from flask import request, send_file
from io import BytesIO
import openpyxl
from datetime import datetime

from flask import request, send_file
from io import BytesIO
import openpyxl
from datetime import datetime, timedelta
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

    schedules = Schedule.query.join(User).join(Shift) \
        .filter(Schedule.work_date.between(start_date, end_date)) \
        .order_by(Schedule.user_id, Schedule.work_date).all()

    print(f"[DEBUG] Found {len(schedules)} schedule entries")  # 🚧 debug

    grouped = {}
    for s in schedules:
        key = (s.user.department or 'Khác', s.user.position or '')
        day_key = s.work_date.strftime('%a %d/%m')

        # Lọc chỉ những ca có từ "trực"
        if 'trực' in s.shift.name.lower():
            grouped.setdefault(key, {})
            grouped[key].setdefault(day_key, "")
            grouped[key][day_key] += f"{s.user.name} ({s.shift.name})\n"

    # Loại bỏ các dòng không có nội dung ca trực nào
    grouped = {k: v for k, v in grouped.items() if any(v.values())}

    date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    print("[DEBUG] Grouped keys:", grouped.keys())

    return render_template('report_all.html',
                           grouped=grouped,
                           date_range=date_range,
                           start_date=start_date,
                           end_date=end_date)

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
    if session.get('role') not in ['admin', 'manager']:
        return "Chỉ admin hoặc manager được phép tạo lịch ca trực."

    user_role = session.get('role')
    user_dept = session.get('department')

    if user_role == 'admin':
        departments = [d[0] for d in db.session.query(User.department).filter(User.department != None).distinct().all()]
    else:
        departments = [user_dept]

    selected_department = (
        request.form.get('department') if request.method == 'POST'
        else request.args.get('department') or (departments[0] if departments else None)
    )

    if user_role != 'admin':
        selected_department = user_dept

    selected_config = CaConfiguration.query.filter_by(department=selected_department).first() if selected_department else None

    model_type = request.form.get('model_type') if request.method == 'POST' else None
    start_date_str = request.form.get('start_date') if request.method == 'POST' else None
    end_date_str = request.form.get('end_date') if request.method == 'POST' else None

    if request.method == 'POST':
        if not start_date_str or not end_date_str:
            return render_template('generate_ca_form.html',
                                   departments=departments,
                                   selected_department=selected_department,
                                   selected_config=selected_config,
                                   model_type=model_type,
                                   start_date=start_date_str,
                                   end_date=end_date_str,
                                   message="Vui lòng chọn đầy đủ ngày bắt đầu và kết thúc.")

        try:
            start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return render_template('generate_ca_form.html',
                                   departments=departments,
                                   selected_department=selected_department,
                                   selected_config=selected_config,
                                   model_type=model_type,
                                   start_date=start_date_str,
                                   end_date=end_date_str,
                                   message="Định dạng ngày không hợp lệ.")

        if not selected_config:
            return render_template('generate_ca_form.html',
                                   departments=departments,
                                   selected_department=selected_department,
                                   selected_config=None,
                                   model_type=model_type,
                                   start_date=start_date_str,
                                   end_date=end_date_str,
                                   message="Chưa cấu hình ca cho khoa này.")

        cas = Ca.query.filter_by(department=selected_department).all()
        shifts = Shift.query.all()
        if not cas or not shifts:
            return render_template('generate_ca_form.html',
                                   departments=departments,
                                   selected_department=selected_department,
                                   selected_config=selected_config,
                                   model_type=model_type,
                                   start_date=start_date_str,
                                   end_date=end_date_str,
                                   message="Chưa có ca hoặc ca trực (shift) nào được tạo cho khoa này.")

        def generate_2ca3kip_pattern(i):
            cycle = [
                [("Ca 1", "day"), ("Ca 2", "night")],
                [("Ca 3", "day"), ("Ca 1", "night")],
                [("Ca 2", "day"), ("Ca 3", "night")],
            ]
            return cycle[i % 3]

        def generate_3ca4kip_pattern(i):
            cycle = [
                [("Ca 1", "morning"), ("Ca 2", "afternoon"), ("Ca 3", "night")],
                [("Ca 4", "morning"), ("Ca 1", "afternoon"), ("Ca 2", "night")],
                [("Ca 3", "morning"), ("Ca 4", "afternoon"), ("Ca 1", "night")],
                [("Ca 2", "morning"), ("Ca 3", "afternoon"), ("Ca 4", "night")],
            ]
            return cycle[i % 4]

        date_range = [start + timedelta(days=i) for i in range((end - start).days + 1)]
        assignments = []
        ca_index = 0

        for i, day in enumerate(date_range):
            if model_type == '2ca3kip':
                shift_names = generate_2ca3kip_pattern(i)
            elif model_type == '3ca4kip':
                shift_names = generate_3ca4kip_pattern(i)
            else:
                shift_names = [s.name for s in shifts[:selected_config.num_shifts]]

            for name in shift_names:
                shift = next((s for s in shifts if s.name == name), None)
                if not shift:
                    continue
                ca = cas[ca_index % len(cas)]
                assignments.extend([
                    Schedule(user_id=ca.doctor_id, shift_id=shift.id, work_date=day),
                    Schedule(user_id=ca.nurse1_id, shift_id=shift.id, work_date=day),
                    Schedule(user_id=ca.nurse2_id, shift_id=shift.id, work_date=day),
                ])
                ca_index += 1

        db.session.add_all(assignments)
        db.session.commit()
        flash("✅ Đã tạo lịch tự động theo tua thành công.", "success")
        return redirect('/schedule')

    return render_template('generate_ca_form.html',
                           departments=departments,
                           selected_department=selected_department,
                           selected_config=selected_config,
                           model_type=model_type,
                           start_date=start_date_str,
                           end_date=end_date_str)

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

    # Lấy danh sách phòng khám, loại bỏ phòng "tiếp đón" để tránh trùng
    rooms = [room for room in ClinicRoom.query.all() if "tiếp đón" not in room.name.lower()]

    # Chuẩn bị dữ liệu lịch
    clinic_schedule = {
        "tiep_don": defaultdict(str),
        "phong_kham": {room.name: defaultdict(str) for room in rooms}
    }

    # Truy xuất lịch trực cho ca có tên chứa "phòng khám" hoặc "tiếp đón"
    schedules = Schedule.query.join(User).join(Shift).filter(
        Schedule.work_date.between(start_date, end_date),
        Shift.name.ilike('%phòng khám%') | Shift.name.ilike('%tiếp đón%')
    ).all()

    user_positions = {}  # <-- Tạo từ điển tên -> chức danh
    for s in schedules:
        user_name = s.user.name
        user_positions[user_name] = s.user.position
        shift_name = s.shift.name.lower()
        day = s.work_date

        if "tiếp đón" in shift_name:
            clinic_schedule["tiep_don"][day] += f"{user_name}\n"
        elif "phòng khám" in shift_name:
            for room in rooms:
                if room.name.lower() in shift_name:
                    clinic_schedule["phong_kham"][room.name][day] += f"{user_name}\n"
                    break

    return render_template(
        'print-clinic-schedule.html',
        start_date=start_date,
        end_date=end_date,
        date_range=date_range,
        clinic_schedule=clinic_schedule,
        user_positions=user_positions,  # <-- Truyền vào template
        now=datetime.now()
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

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])

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

@app.context_processor
def inject_helpers():
    return dict(get_titled_names=get_titled_names)

@app.route('/schedule/lock', methods=['POST'])
def lock_schedule():
    if 'user_id' not in session:
        return "Unauthorized", 401

    department = request.form.get('department')
    start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
    end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()

    # Kiểm tra đã khóa trước đó chưa
    existing = ScheduleLock.query.filter_by(department=department)\
        .filter(ScheduleLock.start_date <= start_date, ScheduleLock.end_date >= end_date).first()

    if existing:
        return "Đã khóa trước đó", 400

    lock = ScheduleLock(
        department=department,
        start_date=start_date,
        end_date=end_date,
        locked_by=session.get('user_id')
    )
    db.session.add(lock)
    db.session.commit()
    return redirect(f'/schedule?department={department}&start_date={start_date}&end_date={end_date}')

@app.route('/schedule/unlock', methods=['POST'])
def unlock_schedule():
    department = request.form.get('department')
    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')

    signature = ScheduleSignature.query.filter_by(
        department=department,
        from_date=from_date,
        to_date=to_date
    ).first()

    if not signature:
        flash('Không tìm thấy bản đã ký.', 'danger')
        return redirect(url_for('view_schedule', department=department, start_date=from_date, end_date=to_date))

    # Xoá bản ghi xác nhận
    db.session.delete(signature)

    # Mở khoá nếu có
    lock = ScheduleLock.query.filter_by(
        department=department,
        start_date=from_date,
        end_date=to_date
    ).first()
    if lock:
        db.session.delete(lock)

    db.session.commit()
    flash('Đã hủy ký và mở khóa lịch trực.', 'success')
    return redirect(url_for('view_schedule', department=department, start_date=from_date, end_date=to_date))

from models.user import User

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)