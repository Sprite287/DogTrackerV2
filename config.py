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

    # Directly use what was read from the environment, or a simple fallback
    SQLALCHEMY_DATABASE_URI = _db_url_from_env if _db_url_from_env else 'sqlite:///this_is_a_fallback.db'

    


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