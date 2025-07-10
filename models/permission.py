from extensions import db

class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    module_name = db.Column(db.String(100), nullable=False)
    can_access = db.Column(db.Boolean, default=True)

    user = db.relationship('User', backref='permissions')
