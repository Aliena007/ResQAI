from app import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )
    password = db.Column(
        db.String(255),
        nullable=False
    )
    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )
    
    def __repr__(self):
        return f"<User {self.username}>"


class IncidentReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    reported_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    severity = db.Column(db.Integer, nullable=False, default=1)
    category = db.Column(db.String(80), nullable=False, default="other")
    status = db.Column(db.String(30), nullable=False, default="reported")
    summary = db.Column(db.Text, nullable=True)
    recommended_action = db.Column(db.Text, nullable=True)
    analysis_provider = db.Column(db.String(30), nullable=False, default="fallback")
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.now())

    reporter = db.relationship("User", backref=db.backref("incident_reports", lazy=True))