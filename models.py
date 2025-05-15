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
    approx_age = db.Column(db.String(50), nullable=True) # New field for approximate age
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Foreign Key to Rescue
    rescue_id = db.Column(db.String(32), db.ForeignKey('rescues.id'), nullable=False, index=True)

    # Relationships to Meds/Appts (add later)
    medicines = db.relationship('Medicine', back_populates='dog', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Dog {self.name}>'

class Medicine(db.Model):
    __tablename__ = 'medicine'
    id = db.Column(db.String(32), primary_key=True, default=lambda: uuid.uuid4().hex) # Changed String(36) to String(32) and default to uuid.uuid4().hex
    name = db.Column(db.String(100), nullable=False)
    dosage = db.Column(db.String(100))
    frequency = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    
    dog_id = db.Column(db.String(32), db.ForeignKey('dogs.id'), nullable=False)
    rescue_id = db.Column(db.String(32), db.ForeignKey('rescues.id'), nullable=False) # For data integrity/scoping

    # Relationship back to Dog (many medicines to one dog)
    dog = db.relationship('Dog', back_populates='medicines')

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Medicine {self.name} for Dog ID {self.dog_id}>"

# --- Add Medicine, Appointment, MedicineLog models later ---