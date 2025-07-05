from extensions import db

class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(255))
    location = db.Column(db.String(255))
    birth_date = db.Column(db.Date)

    user = db.relationship('User', back_populates='leave_requests')


