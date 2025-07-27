from models import db

class WorkRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ngay_thang = db.Column(db.String(50))
    khoa = db.Column(db.String(100))
    loi = db.Column(db.String(255))
    so_ho_so = db.Column(db.String(50))
    so_phieu = db.Column(db.String(50))
    noi_dung = db.Column(db.Text)
    nguoi_yeu_cau = db.Column(db.String(100))
    so_dien_thoai = db.Column(db.String(20))
    chu_ky = db.Column(db.String(50))
    hoa = db.Column(db.String(2))
    hiep = db.Column(db.String(2))
    anh = db.Column(db.String(2))
    nam = db.Column(db.String(2))
