# DogTrackerV2/config.py
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env')) # This loads .env into os.environ

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a_default_secret_key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = False

    # Directly get from environment here, with the fallback
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///this_is_a_fallback.db')
    
    # --- You might want to reinstate the SQLite path adjustment logic here if needed ---
    # --- Make sure to use self.SQLALCHEMY_DATABASE_URI if inside a method, ---
    # --- or Config.SQLALCHEMY_DATABASE_URI if outside but referencing the class attr. ---
    # --- Or adjust this static attribute directly: ---
    _temp_uri = SQLALCHEMY_DATABASE_URI # Use a temp var to avoid direct re-assignment issues in class def
    if _temp_uri and _temp_uri.startswith('sqlite:///instance'):
        instance_path = os.path.join(basedir, 'instance')
        os.makedirs(instance_path, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(instance_path, "dogtracker_v2.db")}'
    elif _temp_uri and _temp_uri.startswith('sqlite:///'): # simple relative path for sqlite
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(basedir, _temp_uri.split("sqlite:///")[-1])}'
    # -----------------------------------------------------------------------------

class DevelopmentConfig(Config):
    DEBUG = True
    # SQLALCHEMY_ECHO = True # Useful for seeing SQL queries

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')

class ProductionConfig(Config):
    # Production specific settings would go here
    pass

config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig # Default to Development for flask run
}