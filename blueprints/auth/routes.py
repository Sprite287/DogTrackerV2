from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from extensions import db
from models import User, Rescue
from forms import LoginForm, RegistrationForm, RescueRegistrationForm, PasswordResetRequestForm, PasswordResetForm
from audit import log_audit_event
from flask_mail import Message, Mail

# Create auth blueprint with no URL prefix to maintain current URLs
auth_bp = Blueprint('auth', __name__, url_prefix='')

# Initialize mail (will be configured by app)
mail = None
limiter = None

def init_mail(app_mail):
    """Initialize mail object for use in auth blueprint"""
    global mail
    mail = app_mail

def init_limiter(app_limiter):
    """Initialize limiter object for use in auth blueprint"""
    global limiter
    limiter = app_limiter

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login with rate limiting and audit logging"""
    
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'danger')
                return render_template('auth/login.html', form=form)
            if not user.email_verified:
                flash('Please verify your email before logging in. Check your inbox for the verification link.', 'warning')
                return render_template('auth/login.html', form=form)
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            # Log successful login
            log_audit_event(
                user_id=user.id,
                rescue_id=user.rescue_id,
                action='login_success',
                resource_type='User',
                resource_id=user.id,
                details={'email': user.email},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                success=True
            )
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.dashboard')
            return redirect(next_page)
        else:
            # Log failed login attempt
            log_audit_event(
                user_id=None,
                rescue_id=None,
                action='login_failed',
                resource_type='User',
                resource_id=None,
                details={'email': form.email.data, 'reason': 'invalid_credentials'},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                success=False
            )
            flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout with audit logging"""
    # Log logout
    log_audit_event(
        user_id=current_user.id,
        rescue_id=current_user.rescue_id,
        action='logout',
        resource_type='User',
        resource_id=current_user.id,
        details={'email': current_user.email},
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )
    
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Individual user registration (redirects to rescue registration)"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # This is for individual user registration (not rescue registration)
        # For now, redirect to rescue registration
        flash('Please register your rescue organization first.', 'info')
        return redirect(url_for('auth.register_rescue'))
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/register-rescue', methods=['GET', 'POST'])
def register_rescue():
    """Rescue organization registration with first user creation"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RescueRegistrationForm()
    if form.validate_on_submit():
        # Create rescue
        rescue = Rescue(
            name=form.rescue_name.data,
            address=form.rescue_address.data,
            phone=form.rescue_phone.data,
            email=form.rescue_email.data,
            primary_contact_name=form.contact_name.data,
            primary_contact_email=form.contact_email.data,
            primary_contact_phone=form.contact_phone.data,
            data_consent=form.data_consent.data,
            marketing_consent=form.marketing_consent.data,
            status='active'  # No admin approval needed
        )
        db.session.add(rescue)
        db.session.flush()  # Get the rescue ID
        
        # Create first user (admin of the rescue)
        user = User(
            name=form.contact_name.data,
            email=form.contact_email.data,
            role='admin',
            rescue_id=rescue.id,
            is_first_user=True,
            email_verified=False,  # Will need email verification
            data_consent=form.data_consent.data,
            marketing_consent=form.marketing_consent.data
        )
        user.set_password(form.contact_password.data)
        token = user.generate_email_verification_token()
        db.session.add(user)
        db.session.commit()
        
        # Send verification email
        verification_url = url_for('auth.verify_email', token=token, _external=True)
        try:
            msg = Message(
                subject="Verify your DogTracker account",
                recipients=[user.email],
                body=f"Hello {user.name},\n\nPlease verify your email by clicking the link below:\n{verification_url}\n\nIf you did not register, please ignore this email."
            )
            mail.send(msg)
        except Exception as e:
            print(f"[EMAIL ERROR] Failed to send verification email: {e}")
            flash('Registration successful, but failed to send verification email. Please contact support.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Log rescue registration
        log_audit_event(
            user_id=user.id,
            rescue_id=rescue.id,
            action='rescue_registration',
            resource_type='Rescue',
            resource_id=rescue.id,
            details={
                'rescue_name': rescue.name,
                'primary_contact_email': rescue.primary_contact_email,
                'status': rescue.status
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            success=True
        )
        
        flash('Registration successful! Please check your email to verify your account before logging in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register_rescue.html', form=form)

@auth_bp.route('/password-reset-request', methods=['GET', 'POST'])
def password_reset_request():
    """Password reset request with rate limiting"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_password_reset_token()
            db.session.commit()
            
            # Log password reset request
            log_audit_event(
                user_id=user.id,
                rescue_id=user.rescue_id,
                action='password_reset_request',
                resource_type='User',
                resource_id=user.id,
                details={'email': user.email},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                success=True
            )
            
            # TODO: Send email with reset link
            # For now, just show a message
            flash(f'Password reset instructions have been sent to {form.email.data}. (Note: Email functionality not yet implemented)', 'info')
        else:
            # Don't reveal if email exists or not for security
            flash(f'If an account with email {form.email.data} exists, password reset instructions have been sent.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/password_reset_request.html', form=form)

@auth_bp.route('/password-reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    """Password reset with token validation"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    user = User.query.filter_by(password_reset_token=token).first()
    if not user or not user.verify_password_reset_token(token):
        flash('Invalid or expired password reset token.', 'danger')
        return redirect(url_for('auth.login'))
    
    form = PasswordResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.password_reset_token = None
        user.password_reset_expires = None
        db.session.commit()
        
        # Log successful password reset
        log_audit_event(
            user_id=user.id,
            rescue_id=user.rescue_id,
            action='password_reset_success',
            resource_type='User',
            resource_id=user.id,
            details={'email': user.email},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            success=True
        )
        
        flash('Your password has been reset successfully. You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/password_reset.html', form=form)

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    """Email verification with token validation"""
    user = User.query.filter_by(email_verification_token=token).first()
    if not user:
        flash('Invalid or expired verification link.', 'danger')
        return redirect(url_for('auth.login'))
    
    user.email_verified = True
    user.email_verification_token = None
    db.session.commit()
    
    # Log email verification
    log_audit_event(
        user_id=user.id,
        rescue_id=user.rescue_id,
        action='email_verification',
        resource_type='User',
        resource_id=user.id,
        details={'email': user.email},
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )
    
    return render_template('auth/email_verified.html')