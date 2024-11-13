from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from tmdb_search import search_movie, search_tv_show
from nyt_api import nyt
import requests

from dotenv import load_dotenv
import os

app = Flask(__name__)

load_dotenv()
tmdb_api_key = os.getenv("TMDB_API_KEY")
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"
NYT_API_KEY = os.getenv("NYT_API_KEY")

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
app.config["SECRET_KEY"] = "abc"
db = SQLAlchemy()
 
login_manager = LoginManager()
login_manager.init_app(app)
 
class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    favorites = db.relationship('Favorite', backref='user', lazy=True)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # "movie" or "tv"
    tmdb_id = db.Column(db.Integer, nullable=False)  # Unique ID from TMDb
    poster_url = db.Column(db.String(300))  # URL to the poster image
 
db.init_app(app)
 
with app.app_context():
    db.create_all()
 
@login_manager.user_loader
def loader_user(user_id):
    return Users.query.get(user_id)
 
@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = Users(username=request.form.get("username"),
                     password=request.form.get("password"))
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("sign_up.html")
 
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = Users.query.filter_by(
            username=request.form.get("username")).first()
        if user.password == request.form.get("password"):
            login_user(user)
            return redirect(url_for("home"))
    return render_template("login.html")
 
@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("home"))
 
@app.route("/")
def home():
    return render_template("home.html")

@app.route('/movies/popular', methods=['GET'])
def popular_movies():
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={tmdb_api_key}"

    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        
        for movie in data['results']:
            if movie['poster_path']:
                movie['poster_url'] = f"{TMDB_IMAGE_BASE_URL}w500{movie['poster_path']}"
            else:
                movie['poster_url'] = "https://via.placeholder.com/500x750?text=No+Image"

        # Render the movies.html template and pass the movie data
        return render_template("movies.html", movies=data['results'])
    else:
        return "Unable to fetch popular movies", response.status_code  
    
@app.route('/tv/popular', methods=['GET'])
def popular_tvshows():
    url = f"https://api.themoviedb.org/3/tv/popular?api_key={tmdb_api_key}"

    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        
        for tv in data['results']:
            if tv['poster_path']:
                tv['poster_url'] = f"{TMDB_IMAGE_BASE_URL}w500{tv['poster_path']}"
            else:
                tv['poster_url'] = "https://via.placeholder.com/500x750?text=No+Image"

        # Render the movies.html template and pass the movie data
        return render_template("tvshows.html", tvs=data['results'])
    else:
        return "Unable to fetch popular tv shows", response.status_code  

@app.route('/bestsellers')
def bestsellers():
    books = nyt.best_sellers_list()
    if books is None:
        return "Error fetching bestsellers data", 500
    return render_template("bestsellers.html", books=books)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    category = request.args.get('category')

    if not query:
        return "Please provide a search query."

    if category == "movie":
        results = search_movie(query)
    elif category == "tv":
        results = search_tv_show(query)
    elif category == "book":
        return render_template("book_review.html", reviews=nyt.book_reviews(title=query), title=query)
    elif category == "author":
        return render_template("book_review.html", reviews=nyt.book_reviews(author=query), title=query)
    else:
        return "Please specify a valid category."

    return render_template("search_results.html", results=results, category=category)

@app.route('/add_favorite', methods=['POST'])
@login_required
def add_favorite():
    title = request.form.get('title')
    media_type = request.form.get('type')  # "movie" or "tv"
    tmdb_id = request.form.get('tmdb_id')
    poster_url = request.form.get('poster_url')

    # Check if this favorite already exists for the user
    existing_favorite = Favorite.query.filter_by(user_id=current_user.id, tmdb_id=tmdb_id).first()
    if existing_favorite:
        flash("This item is already in your favorites.", "info")
        return redirect(url_for('favorites'))

    # Add new favorite
    new_favorite = Favorite(user_id=current_user.id, title=title, type=media_type, tmdb_id=tmdb_id, poster_url=poster_url)
    db.session.add(new_favorite)
    db.session.commit()
    flash("Added to favorites!", "success")
    return redirect(url_for('favorites'))

if __name__ == '__main__':
    app.run(debug=True)