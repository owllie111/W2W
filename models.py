from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Users(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    profile_picture = db.Column(db.String(300), nullable=True)  # Path to the profile picture
    favorites = db.relationship('Favorite', backref='user', lazy=True)  # Link to favorites
    comments = db.relationship('Comment', backref='user', lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"

class Favorite(db.Model):
    __tablename__ = 'favorites' 
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, nullable=True)
    tv_id = db.Column(db.Integer, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<Favorite {self.id}>'
    
class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Link to Users table
    media_id = db.Column(db.Integer, nullable=False)  # ID of the movie or TV show
    media_type = db.Column(db.String(10), nullable=False)  # 'movie' or 'tv'
    content = db.Column(db.Text, nullable=False)  # User's review
    created_at = db.Column(db.DateTime, default=db.func.now())  # Timestamp

    def __repr__(self):
        return f'<Comment {self.id}>'
