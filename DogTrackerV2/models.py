from .extensions import db
from sqlalchemy.orm import relationship
from datetime import datetime, date

class Rescue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    users = relationship('User', backref='rescue', lazy=True)
    dogs = relationship('Dog', backref='rescue', lazy=True)
    appointment_types = relationship('AppointmentType', backref='rescue', lazy=True)
    medicine_presets = relationship('MedicinePreset', backref='rescue', lazy=True)

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
    medicines = relationship('DogMedicine', backref='dog', lazy=True, cascade='all, delete-orphan')

class AppointmentType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rescue_id = db.Column(db.Integer, db.ForeignKey('rescue.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(20), default='#007bff')
    appointments = relationship('Appointment', backref='type', lazy=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dog_id = db.Column(db.Integer, db.ForeignKey('dog.id'), nullable=False)
    rescue_id = db.Column(db.Integer, db.ForeignKey('rescue.id'), nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime)
    recurrence = db.Column(db.String(20))  # none, daily, weekly, monthly, yearly, every_x_days, custom_text
    recurrence_value = db.Column(db.Integer)  # for every_x_days
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, canceled
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reminders = relationship('Reminder', backref='appointment', lazy=True, cascade='all, delete-orphan')

class MedicinePreset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rescue_id = db.Column(db.Integer, db.ForeignKey('rescue.id'), nullable=True)  # null = global preset
    name = db.Column(db.String(120), nullable=False)
    default_unit = db.Column(db.String(20))
    notes = db.Column(db.Text)
    medicines = relationship('DogMedicine', backref='preset', lazy=True)

class DogMedicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dog_id = db.Column(db.Integer, db.ForeignKey('dog.id'), nullable=False)
    rescue_id = db.Column(db.Integer, db.ForeignKey('rescue.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicine_preset.id'), nullable=True)  # null if custom
    custom_name = db.Column(db.String(120))
    dosage = db.Column(db.String(50))
    unit = db.Column(db.String(20))
    frequency = db.Column(db.String(20))  # daily, weekly, monthly, as_needed, every_x_days, custom_text
    frequency_value = db.Column(db.Integer)  # for every_x_days
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')  # active, completed, stopped
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reminders = relationship('Reminder', backref='dog_medicine', lazy=True, cascade='all, delete-orphan')
    history = relationship('DogMedicineHistory', backref='dog_medicine', lazy=True, cascade='all, delete-orphan')

class Reminder(db.Model):
    __tablename__ = 'reminder'
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    due_datetime = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True) # e.g., pending, acknowledged, dismissed
    reminder_type = db.Column(db.String(50), nullable=False, index=True) # e.g., appointment_upcoming, medicine_due

    dog_id = db.Column(db.Integer, db.ForeignKey('dog.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=True)
    dog_medicine_id = db.Column(db.Integer, db.ForeignKey('dog_medicine.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    dog = relationship('Dog', backref=db.backref('reminders', lazy=True, cascade='all, delete-orphan'))
    # The 'appointment' backref is already defined in the Appointment model's 'reminders' relationship.
    # The 'dog_medicine' backref is already defined in the DogMedicine model's 'reminders' relationship.
    user = relationship('User', backref=db.backref('created_reminders', lazy=True)) # User who might have created/triggered this reminder

class DogMedicineHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dog_medicine_id = db.Column(db.Integer, db.ForeignKey('dog_medicine.id'), nullable=False)
    date_given = db.Column(db.Date, default=date.today)
    given_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    notes = db.Column(db.Text) 