from extensions import db
from sqlalchemy.orm import relationship
from datetime import datetime, date, timedelta
from sqlalchemy import Index
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

class Rescue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    address = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    
    # Phase 6A.2: Registration and approval fields
    status = db.Column(db.String(20), default='pending')  # pending, approved, suspended
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    approved_date = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Contact information for registration
    primary_contact_name = db.Column(db.String(120))
    primary_contact_email = db.Column(db.String(120), unique=True)
    primary_contact_phone = db.Column(db.String(50))
    
    # Consent tracking
    data_consent = db.Column(db.Boolean, default=False)
    marketing_consent = db.Column(db.Boolean, default=False)
    
    users = relationship('User', backref='rescue', lazy=True, foreign_keys='User.rescue_id')
    dogs = relationship('Dog', backref='rescue', lazy=True)
    appointment_types = relationship('AppointmentType', backref='rescue', lazy=True)
    medicine_presets = relationship('MedicinePreset', backref='rescue', lazy=True)
    approver = relationship('User', foreign_keys=[approved_by], backref='approved_rescues')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'staff', 'superadmin'
    
    # Authentication and account management
    is_active = db.Column(db.Boolean, default=True)
    is_first_user = db.Column(db.Boolean, default=False)  # First user of a rescue becomes admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Email verification
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100))
    
    # Password reset
    password_reset_token = db.Column(db.String(100))
    password_reset_expires = db.Column(db.DateTime)
    
    # Consent tracking
    data_consent = db.Column(db.Boolean, default=False)
    marketing_consent = db.Column(db.Boolean, default=False)
    
    # Legacy fields (keeping for backward compatibility)
    device_id = db.Column(db.String(255))  # For device auth
    invite_code = db.Column(db.String(32))
    can_edit = db.Column(db.Boolean, default=False)
    
    rescue_id = db.Column(db.Integer, db.ForeignKey('rescue.id'), nullable=True)  # Nullable for superadmin
    
    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash."""
        return check_password_hash(self.password_hash, password)
    
    def generate_email_verification_token(self):
        """Generate a secure token for email verification."""
        self.email_verification_token = secrets.token_urlsafe(32)
        return self.email_verification_token
    
    def generate_password_reset_token(self, expires_in=3600):
        """Generate a secure token for password reset."""
        self.password_reset_token = secrets.token_urlsafe(32)
        self.password_reset_expires = datetime.utcnow() + timedelta(seconds=expires_in)
        return self.password_reset_token
    
    def verify_password_reset_token(self, token):
        """Verify password reset token is valid and not expired."""
        return (self.password_reset_token == token and 
                self.password_reset_expires and 
                self.password_reset_expires > datetime.utcnow())
    
    def is_superadmin(self):
        """Check if user is a superadmin."""
        return self.role == 'superadmin'
    
    def is_rescue_admin(self):
        """Check if user is an admin of their rescue."""
        return self.role in ['admin', 'superadmin']
    
    def can_access_rescue(self, rescue_id):
        """Check if user can access data for a specific rescue."""
        if self.is_superadmin():
            return True
        return self.rescue_id == rescue_id

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
    creator = relationship('User', foreign_keys=[created_by], backref=db.backref('created_appointments', lazy=True))

class MedicinePreset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rescue_id = db.Column(db.Integer, db.ForeignKey('rescue.id'), nullable=True)  # null = global preset
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(100), nullable=True) # Added: e.g., Antibiotic, NSAID, Parasite Control
    default_dosage_instructions = db.Column(db.Text, nullable=True) # Added: General dosing info/guidelines
    suggested_units = db.Column(db.String(255), nullable=True) # Added: Comma-separated like 'mg,ml,tablet'
    default_unit = db.Column(db.String(20), nullable=True) # Changed: Made nullable
    notes = db.Column(db.Text)
    medicines = relationship('DogMedicine', backref='preset', lazy=True)

class DogMedicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dog_id = db.Column(db.Integer, db.ForeignKey('dog.id'), nullable=False)
    rescue_id = db.Column(db.Integer, db.ForeignKey('rescue.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicine_preset.id'), nullable=True)  # null if custom
    custom_name = db.Column(db.String(120))
    dosage = db.Column(db.String(50))
    unit = db.Column(db.String(50), nullable=False)
    form = db.Column(db.String(100), nullable=True)  # e.g., "Tablet (Oral)", "Injectable (Solution)"
    frequency = db.Column(db.String(100), nullable=False)
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
    creator = relationship('User', foreign_keys=[created_by], backref=db.backref('created_dog_medicines', lazy=True))

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

class DogNote(db.Model):
    __tablename__ = 'dog_note'
    id = db.Column(db.Integer, primary_key=True)
    dog_id = db.Column(db.Integer, db.ForeignKey('dog.id'), nullable=False)
    rescue_id = db.Column(db.Integer, db.ForeignKey('rescue.id'), nullable=False) # Assuming notes are also rescue-specific
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # User who created the note
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    note_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False) # e.g., Medical Observation, Behavioral Note, etc.

    # Relationships
    dog = relationship('Dog', backref=db.backref('care_notes', lazy='dynamic', cascade='all, delete-orphan'))
    user = relationship('User', backref=db.backref('dog_notes_created', lazy=True))
    rescue = relationship('Rescue', backref=db.backref('dog_notes', lazy=True))

    # Consider adding an __repr__ for easier debugging
    def __repr__(self):
        return f"<DogNote {self.id} - Dog {self.dog_id} - Category {self.category}>"

class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    rescue_id = db.Column(db.Integer, db.ForeignKey('rescue.id'), nullable=True, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(100), nullable=True, index=True)
    resource_id = db.Column(db.Integer, nullable=True, index=True)
    details = db.Column(db.JSON, nullable=True)
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text, nullable=True)
    execution_time = db.Column(db.Float, nullable=True)
    occurrence_count = db.Column(db.Integer, default=1)
    last_occurrence = db.Column(db.DateTime, nullable=True)

    user = relationship('User', backref=db.backref('audit_logs', lazy=True))
    rescue = relationship('Rescue', backref=db.backref('audit_logs', lazy=True))

    __table_args__ = (
        Index('ix_audit_log_rescue_id_timestamp', 'rescue_id', 'timestamp'),
        Index('ix_audit_log_user_id_action_timestamp', 'user_id', 'action', 'timestamp'),
        Index('ix_audit_log_resource_type_id_timestamp', 'resource_type', 'resource_id', 'timestamp'),
    )

    def __repr__(self):
        return f"<AuditLog {self.id} {self.action} {self.resource_type} {self.resource_id} user={self.user_id} rescue={self.rescue_id}>" 