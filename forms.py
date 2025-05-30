from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Regexp
from models import User, Rescue
import difflib
import re

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long'),
        Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', message='Password must include uppercase, lowercase, a number, and a special character (e.g., @, $, !, %, *, ?, &).')
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])
    data_consent = BooleanField('I consent to the processing of my personal data', validators=[DataRequired()])
    marketing_consent = BooleanField('I consent to receiving marketing communications (optional)')
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email address already registered. Please use a different email.')

class RescueRegistrationForm(FlaskForm):
    # Rescue Information
    rescue_name = StringField('Rescue Organization Name', validators=[DataRequired(), Length(min=2, max=120)])
    rescue_address = TextAreaField('Address')
    rescue_phone = StringField('Phone Number')
    rescue_email = StringField('Rescue Email', validators=[Email()])
    
    # Primary Contact (First User)
    contact_name = StringField('Primary Contact Name', validators=[DataRequired(), Length(min=2, max=120)])
    contact_email = StringField('Primary Contact Email', validators=[DataRequired(), Email()])
    contact_phone = StringField('Primary Contact Phone')
    contact_password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long'),
        Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', message='Password must include uppercase, lowercase, a number, and a special character (e.g., @, $, !, %, *, ?, &).')
    ])
    contact_password2 = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('contact_password', message='Passwords must match')
    ])
    
    # Consent
    data_consent = BooleanField('I consent to the processing of personal data for this rescue organization', validators=[DataRequired()])
    marketing_consent = BooleanField('I consent to receiving marketing communications (optional)')
    
    submit = SubmitField('Register Rescue')

    def validate_rescue_name(self, rescue_name):
        # Check for exact match
        existing_rescue = Rescue.query.filter_by(name=rescue_name.data).first()
        if existing_rescue:
            raise ValidationError('A rescue with this exact name already exists. Please choose a different name.')
        
        # Check for similar names (fuzzy matching)
        all_rescues = Rescue.query.all()
        for rescue in all_rescues:
            similarity = difflib.SequenceMatcher(None, rescue_name.data.lower(), rescue.name.lower()).ratio()
            if similarity >= 0.85:  # 85% similarity threshold
                raise ValidationError(f'A rescue with a very similar name "{rescue.name}" already exists. Please choose a more distinct name.')

    def validate_contact_email(self, contact_email):
        # Check if email is already registered
        user = User.query.filter_by(email=contact_email.data).first()
        if user:
            raise ValidationError('This email address is already registered. Please use a different email.')
        
        # Check if email is already used as primary contact for another rescue
        rescue = Rescue.query.filter_by(primary_contact_email=contact_email.data).first()
        if rescue:
            raise ValidationError('This email is already the primary contact for another rescue.')

    def validate_rescue_email(self, rescue_email):
        if rescue_email.data:
            rescue = Rescue.query.filter_by(email=rescue_email.data).first()
            if rescue:
                raise ValidationError('This email address is already associated with another rescue.')

class PasswordResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class PasswordResetForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long'),
        Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', message='Password must include uppercase, lowercase, a number, and a special character (e.g., @, $, !, %, *, ?, &).')
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')

class AuditForm(FlaskForm):
    # This form is intentionally empty, as it only needs CSRF protection
    pass 