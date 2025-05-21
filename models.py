from extensions import db
from sqlalchemy.orm import relationship
from datetime import datetime

class Rescue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    users = relationship('User', backref='rescue', lazy=True)
    dogs = relationship('Dog', backref='rescue', lazy=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'owner' or 'staff'
    device_id = db.Column(db.String(255))  # For device auth
    invite_code = db.Column(db.String(32))
    can_edit = db.Column(db.Boolean, default=False)
    rescue_id = db.Column(db.Integer, db.ForeignKey('rescue.id'), nullable=False)

class Dog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.String(20))
    breed = db.Column(db.String(120))
    adoption_status = db.Column(db.String(50))
    intake_date = db.Column(db.Date)
    microchip_id = db.Column(db.String(120))
    notes = db.Column(db.Text)
    medical_info = db.Column(db.Text)
    rescue_id = db.Column(db.Integer, db.ForeignKey('rescue.id'), nullable=False)
    appointments = relationship('Appointment', backref='dog', lazy=True, cascade='all, delete-orphan')

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dog_id = db.Column(db.Integer, db.ForeignKey('dog.id'), nullable=False)
    type = db.Column(db.String(20))  # medication, vet, general, adoption
    date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text)
    recurring = db.Column(db.Boolean, default=False)
    recurrence_pattern = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 