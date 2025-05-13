# DogTrackerV2/models.py
import uuid
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class Rescue(db.Model):
    __tablename__ = 'rescues'
    id = db.Column(db.String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationship to Dogs
    dogs = db.relationship('Dog', backref='rescue', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Rescue {self.name}>'

class Dog(db.Model):
    __tablename__ = 'dogs'
    id = db.Column(db.String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = db.Column(db.String(120), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Foreign Key to Rescue
    rescue_id = db.Column(db.String(32), db.ForeignKey('rescues.id'), nullable=False, index=True)

    # Relationships to Meds/Appts (add later)
    # medicines = db.relationship('Medicine', backref='dog', cascade="all, delete-orphan", lazy=True)
    # appointments = db.relationship('Appointment', backref='dog', cascade="all, delete-orphan", lazy=True)

    def __repr__(self):
        return f'<Dog {self.name}>'

# --- Add Medicine, Appointment, MedicineLog models later ---