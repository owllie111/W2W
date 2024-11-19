import os

class Config:
    SQLALCHEMY_DATABASE_URI = "sqlite:///db.sqlite"
    SECRET_KEY = "yolo"
    STATIC_FOLDER = "static"
    UPLOAD_FOLDER = "static/uploads/"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max file size
    TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    
class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///dev_db.sqlite"


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///test_db.sqlite"


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///prod_db.sqlite")
