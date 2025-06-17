import os
import warnings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration class with common settings."""
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://username:password@localhost:5432/database_name')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB limit for request size
    
    # Session Configuration
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
    SESSION_COOKIE_SAMESITE = 'Lax'  # Mitigate CSRF
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes (in seconds)
    
    # Mail Configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.example.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() in ['true', '1', 'yes']
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'false').lower() in ['true', '1', 'yes']
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'DogTracker <noreply@example.com>')
    
    @classmethod
    def init_app(cls, app):
        """Initialize app with configuration validation."""
        cls.validate_secret_key()
    
    @classmethod
    def validate_secret_key(cls):
        """Validate SECRET_KEY security."""
        MIN_SECRET_KEY_LENGTH = 32
        WEAK_SECRET_KEYS = ['dev', 'secret', 'changeme', 'your-secret-key']
        
        if not cls.SECRET_KEY or len(cls.SECRET_KEY) < MIN_SECRET_KEY_LENGTH:
            warnings.warn(
                f'SECURITY WARNING: SECRET_KEY is missing or too short (less than {MIN_SECRET_KEY_LENGTH} characters). '
                'This is a serious security risk. Please set a strong, random SECRET_KEY environment variable.',
                UserWarning
            )
        elif cls.SECRET_KEY in WEAK_SECRET_KEYS:
            warnings.warn(
                f'SECURITY WARNING: SECRET_KEY is set to a known weak value ("{cls.SECRET_KEY}"). '
                'This is a serious security risk. Please set a strong, random SECRET_KEY environment variable.',
                UserWarning
            )
        else:
            print("SECRET_KEY validation passed.")


class DevelopmentConfig(Config):
    """Development configuration with debug settings enabled."""
    
    DEBUG = True
    
    # Development-specific security settings
    SESSION_COOKIE_SECURE = False  # Allow HTTP cookies in development
    
    # Development settings to prevent caching issues
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0
    
    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        print("Development configuration loaded.")


class ProductionConfig(Config):
    """Production configuration with security hardening."""
    
    DEBUG = False
    
    # Production security settings
    SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
    
    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        print("Production configuration loaded.")
        
        # Additional production validations
        if cls.SECRET_KEY == 'dev':
            raise RuntimeError("Critical security risk: SECRET_KEY is set to default 'dev' value in production.")


class TestingConfig(Config):
    """Testing configuration with appropriate settings for tests."""
    
    TESTING = True
    DEBUG = True
    
    # Use in-memory SQLite for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Test-specific security settings
    SESSION_COOKIE_SECURE = False
    
    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        print("Testing configuration loaded.")


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}