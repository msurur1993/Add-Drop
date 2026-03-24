from datetime import datetime, timezone
from uuid import uuid4

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    ntfy_topic = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        default=lambda: f"addrop-user-{uuid4().hex[:12]}",
    )
    email = db.Column(db.String(200), nullable=True)
    google_id = db.Column(db.String(200), unique=True, nullable=True, index=True)
    name = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    watched_classes = db.relationship("WatchedClass", backref="user", lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="user", lazy=True, cascade="all, delete-orphan")


class WatchedClass(db.Model):
    __tablename__ = "watched_classes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    subject = db.Column(db.String(20), nullable=False)
    catalog_number = db.Column(db.String(20), nullable=False)
    section = db.Column(db.String(10), nullable=True)
    term = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "subject", "catalog_number", "section", "term", name="uq_user_watch"),
    )


class ClassStatus(db.Model):
    __tablename__ = "class_status"

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(20), nullable=False)
    catalog_number = db.Column(db.String(20), nullable=False)
    section = db.Column(db.String(10), nullable=False)
    term = db.Column(db.String(10), nullable=False)
    course_name = db.Column(db.String(200), nullable=True)
    enrolled = db.Column(db.Integer, default=0)
    capacity = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="Unknown")
    instructor = db.Column(db.String(200), nullable=True)
    schedule = db.Column(db.String(200), nullable=True)
    class_nbr = db.Column(db.String(20), nullable=True)
    last_checked = db.Column(db.DateTime, nullable=True)
    last_changed = db.Column(db.DateTime, nullable=True)

    notifications = db.relationship("Notification", backref="class_status", lazy=True)

    __table_args__ = (
        db.UniqueConstraint("subject", "catalog_number", "section", "term", name="uq_class_status"),
    )


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    class_status_id = db.Column(db.Integer, db.ForeignKey("class_status.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
