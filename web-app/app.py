from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from tmdb_search import search_movie, search_tv_show
import requests

from dotenv import load_dotenv
import os

app = Flask(__name__)

load_dotenv()
tmdb_api_key = os.getenv("TMDB_API_KEY")
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"
TEMP_UPLOAD_FOLDER = "temp_uploads"
STATIC_FOLDER = "static"
UPLOAD_FOLDER = "static/uploads"

os.makedirs(TEMP_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
app.config["SECRET_KEY"] = "abc"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(STATIC_FOLDER, 'favicon.ico', mimetype='image/vnd.microsoft.icon')

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

login_manager = LoginManager()
login_manager.init_app(app)
 
db.init_app(app)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def loader_user(user_id):
    return Users.query.get(int(user_id))
 
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

@app.route("/upload_profile_pic", methods=["GET", "POST"])
@login_required
def upload_profile_pic():
    if request.method == "POST":
        if 'user_image' not in request.files: 
            flash('No file part')
            return redirect(url_for('profile'))

        file = request.files['user_image']  
        if file.filename == '':
            flash('No selected file')
            return redirect(url_for('profile'))

        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            base, ext = os.path.splitext(original_filename)
            final_filename = original_filename
            final_file_path = os.path.join(app.config['UPLOAD_FOLDER'], final_filename)

            counter = 1
            while os.path.exists(final_file_path):
                final_filename = f"{base}({counter}){ext}"
                final_file_path = os.path.join(app.config['UPLOAD_FOLDER'], final_filename)
                counter += 1

        temp_file_path = os.path.join(TEMP_UPLOAD_FOLDER, final_filename)
        file.save(temp_file_path)
        print("File temporarily saved at:", temp_file_path)
            
        os.rename(temp_file_path, final_file_path)
        print("File moved to final destination:", final_file_path)

        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print("Temporary file deleted:", temp_file_path)

            current_user.profile_picture = f"uploads/{final_filename}"
            db.session.commit()

            print("Uploaded file path: ", current_user.profile_picture)

            flash('Profile picture uploaded successfully!')
        else:
            flash('Invalid file format')
    
    return render_template("profile.html")

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/recommended')
@login_required
def recommendations():
    # Query the user's favorites
    user_favorites = Favorite.query.filter_by(user_id=current_user.id).all()

    total_movie_genres= set()
    total_tv_genres = set()

    # Fetch genre IDs from each favorite movie or TV show
    for fav in user_favorites:
        if fav.movie_id:
            # Fetch movie details
            response = requests.get(f"https://api.themoviedb.org/3/movie/{fav.movie_id}?api_key={tmdb_api_key}")
            if response.status_code == 200:
                movie = response.json()
                # Add genre IDs to the movie genre ID set
                movie_genres = {movie_genre['id'] for movie_genre in movie.get('genres', [])} 
                total_movie_genres.update(movie_genres)
                print(total_movie_genres)
        elif fav.tv_id:
            # Fetch TV show details
            response = requests.get(f"https://api.themoviedb.org/3/tv/{fav.tv_id}?api_key={tmdb_api_key}")
            if response.status_code == 200:
                tv_show = response.json()
                tv_genres = {tv_genre['id'] for tv_genre in tv_show.get('genres', [])} 
                total_tv_genres.update(tv_genres)
                print(total_tv_genres)

    # Fetch recommended movies based on collected genre IDs
    recommended_movies = []
    if total_movie_genres:
        genre_query = ','.join(map(str, total_movie_genres))
        movie_rec_url = f"https://api.themoviedb.org/3/discover/movie?api_key={tmdb_api_key}&with_genre_ids={genre_query}&sort_by=popularity.desc"
        response = requests.get(movie_rec_url)
        if response.status_code == 200:
            recommended_movies = response.json().get('results', [])

    # Fetch recommended TV shows based on collected genre IDs
    recommended_tv_shows = []
    if total_tv_genres:
        genre_query = ','.join(map(str, total_tv_genres))
        tv_rec_url = f"https://api.themoviedb.org/3/discover/tv?api_key={tmdb_api_key}&with_genre_ids={genre_query}&sort_by=popularity.desc"
        response = requests.get(tv_rec_url)
        if response.status_code == 200:
            recommended_tv_shows = response.json().get('results', [])

    # Combine movie and TV recommendations
    total_recommendations = recommended_movies + recommended_tv_shows

    # Render recommendations in the template
    return render_template('recommendations.html', recommendations=total_recommendations)

@app.route('/favorites', methods=['GET'])
@login_required
def favorites():
    # Query the user's favorites
    user_favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    movie_favorites = []
    tv_favorites = []

    # Fetch movie and TV show details
    for fav in user_favorites:
        if fav.movie_id:
            # Fetch movie details using the movie_id
            response = requests.get(f"https://api.themoviedb.org/3/movie/{fav.movie_id}?api_key={tmdb_api_key}")
            if response.status_code == 200:
                movie = response.json()
                movie['fav_id'] = fav.id  # Add the favorite ID
                movie['media_type'] = 'movie'
                movie_favorites.append(movie)
        elif fav.tv_id:
            # Fetch TV show details using the tv_id
            response = requests.get(f"https://api.themoviedb.org/3/tv/{fav.tv_id}?api_key={tmdb_api_key}")
            if response.status_code == 200:
                tv_show = response.json()
                tv_show['fav_id'] = fav.id  # Add the favorite ID
                tv_show['media_type'] = 'tv'
                tv_favorites.append(tv_show)

        total_favorites = movie_favorites + tv_favorites

    return render_template('favorites.html', faves=total_favorites)

@app.route('/favorite', methods=['POST'])
@login_required  # Ensure user is logged in
def add_to_favorites():
    media_type = request.form.get('media_type')  # 'movie' or 'tv'
    media_id = request.form.get('media_id')
    
    # Check if the media item is already in the favorites
    existing_favorite = Favorite.query.filter_by(
        user_id=current_user.id, 
        movie_id=media_id if media_type == 'movie' else None, 
        tv_id=media_id if media_type == 'tv' else None
    ).first()
    
    if not existing_favorite:
        # Add the new favorite
        favorite = Favorite(
            movie_id=media_id if media_type == 'movie' else None,
            tv_id=media_id if media_type == 'tv' else None,
            user_id=current_user.id
        )
        db.session.add(favorite)
        db.session.commit()
        flash('Added to favorites!', 'success')
    else:
        flash('This item is already in your favorites.', 'info')

    return redirect(request.referrer)

@app.route('/remove_favorite/<int:fav_id>', methods=['GET'])
@login_required  # Ensure user is logged in
def remove_from_favorites(fav_id):
    favorite = Favorite.query.get(fav_id)
    
    if favorite and favorite.user_id == current_user.id:
        db.session.delete(favorite)
        db.session.commit()
        flash('Removed from favorites!', 'success')
    else:
        flash('Error, item not found or unauthorized.', 'danger')

    return redirect(url_for('favorites'))  # Redirect to favorites page

@app.route('/add_comment', methods=['POST'])
@login_required
def add_comment():
    media_id = request.form.get('media_id')
    media_type = request.form.get('media_type')
    content = request.form.get('content')

    if not content.strip():
        flash("Comment cannot be empty.", "danger")
        return redirect(request.referrer)

    # Save the comment
    comment = Comment(
        user_id=current_user.id,
        media_id=media_id,
        media_type=media_type,
        content=content
    )
    db.session.add(comment)
    db.session.commit()

    flash("Your comment has been added!", "success")
    return redirect(request.referrer)

@app.route('/my_comments')
@login_required
def my_comments():
    # Fetch all comments by the current user
    user_comments = Comment.query.filter_by(user_id=current_user.id).all()

    # Add additional info for display
    comments_details = []
    for comment in user_comments:
        if comment.media_type == 'movie':
            # Fetch movie details
            response = requests.get(f"https://api.themoviedb.org/3/movie/{comment.media_id}?api_key={tmdb_api_key}")
            if response.status_code == 200:
                media = response.json()
                comments_details.append({
                    "title": media['title'],
                    "poster_path": media.get('poster_path'),
                    "content": comment.content,
                    "review_url": url_for('movie_reviews', movie_id=comment.media_id),
                    "created_at": comment.created_at
                })
        elif comment.media_type == 'tv':
            # Fetch TV details
            response = requests.get(f"https://api.themoviedb.org/3/tv/{comment.media_id}?api_key={tmdb_api_key}")
            if response.status_code == 200:
                media = response.json()
                comments_details.append({
                    "title": media['name'],
                    "poster_path": media.get('poster_path'),
                    "content": comment.content,
                    "review_url": url_for('tv_reviews', tv_id=comment.media_id),
                    "created_at": comment.created_at
                })

    return render_template('my_comments.html', comments=comments_details)

@app.route('/popular', methods=['GET'])
def popular_movies_and_tvshows():
    # Popular Movies
    movie_url = f"https://api.themoviedb.org/3/movie/popular?api_key={tmdb_api_key}"
    movie_response = requests.get(movie_url)
    
    if movie_response.status_code == 200:
        movie_data = movie_response.json()
        for movie in movie_data['results']:
            if movie['poster_path']:
                movie['poster_url'] = f"{TMDB_IMAGE_BASE_URL}w500{movie['poster_path']}"
            else:
                movie['poster_url'] = "https://via.placeholder.com/500x750?text=No+Image"
    else:
        return "Unable to fetch popular movies", movie_response.status_code  

    # Popular TV Shows
    tv_url = f"https://api.themoviedb.org/3/tv/popular?api_key={tmdb_api_key}"
    tv_response = requests.get(tv_url)
    
    if tv_response.status_code == 200:
        tv_data = tv_response.json()
        for tv in tv_data['results']:
            if tv['poster_path']:
                tv['poster_url'] = f"{TMDB_IMAGE_BASE_URL}w500{tv['poster_path']}"
            else:
                tv['poster_url'] = "https://via.placeholder.com/500x750?text=No+Image"
    else:
        return "Unable to fetch popular tv shows", tv_response.status_code  

    # Render the combined template and pass both movie and tv data
    return render_template("popular.html", movies=movie_data['results'], tvs=tv_data['results'])

@app.route('/movie/review/<int:movie_id>', methods=['GET', 'POST'])
@login_required
def movie_reviews(movie_id):
    reviews_url = f"https://api.themoviedb.org/3/movie/{movie_id}/reviews?api_key={tmdb_api_key}"
    details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={tmdb_api_key}"

    # Handle form submission for user comments
    if request.method == 'POST':
        content = request.form.get('content')
        if content.strip():
            comment = Comment(
                user_id=current_user.id,
                media_id=movie_id,
                media_type='movie',
                content=content
            )
            db.session.add(comment)
            db.session.commit()
            flash("Your comment has been added!", "success")
        else:
            flash("Comment cannot be empty.", "danger")
        return redirect(request.url)  # Redirect to prevent form re-submission

    # Fetch TMDB reviews and details
    reviews_response = requests.get(reviews_url)
    details_response = requests.get(details_url)

    if reviews_response.status_code == 200 and details_response.status_code == 200:
        tmdb_reviews = reviews_response.json().get('results', [])
        movie_details = details_response.json()

        # Fetch user comments from the database
        user_comments = Comment.query.filter_by(media_id=movie_id, media_type='movie').all()

        poster_url = f"{TMDB_IMAGE_BASE_URL}w500{movie_details['poster_path']}" if movie_details.get('poster_path') else "https://via.placeholder.com/500x750?text=No+Image"

        return render_template(
            "movie_review.html",
            tmdb_reviews=tmdb_reviews,
            user_comments=user_comments,
            movie=movie_details,
            poster_url=poster_url
        )
    else:
        return f"Unable to fetch reviews or details for movie {movie_id}", 500

@app.route('/tv/review/<int:tv_id>', methods=['GET', 'POST'])
@login_required
def tv_reviews(tv_id):
    reviews_url = f"https://api.themoviedb.org/3/tv/{tv_id}/reviews?api_key={tmdb_api_key}"
    details_url = f"https://api.themoviedb.org/3/tv/{tv_id}?api_key={tmdb_api_key}"

    # Handle form submission for user comments
    if request.method == 'POST':
        content = request.form.get('content')
        if content.strip():
            comment = Comment(
                user_id=current_user.id,
                media_id=tv_id,
                media_type='tv',
                content=content
            )
            db.session.add(comment)
            db.session.commit()
            flash("Your comment has been added!", "success")
        else:
            flash("Comment cannot be empty.", "danger")
        return redirect(request.url)  # Redirect to prevent form re-submission

    # Fetch TMDB reviews and details
    reviews_response = requests.get(reviews_url)
    details_response = requests.get(details_url)

    if reviews_response.status_code == 200 and details_response.status_code == 200:
        tmdb_reviews = reviews_response.json().get('results', [])
        tv_details = details_response.json()

        # Fetch user comments from the database
        user_comments = Comment.query.filter_by(media_id=tv_id, media_type='tv').all()

        poster_url = f"{TMDB_IMAGE_BASE_URL}w500{tv_details['poster_path']}" if tv_details.get('poster_path') else "https://via.placeholder.com/500x750?text=No+Image"

        return render_template(
            "tv_review.html",
            tmdb_reviews=tmdb_reviews,
            user_comments=user_comments,
            tv=tv_details,
            poster_url=poster_url
        )
    else:
        return f"Unable to fetch reviews or details for TV show {tv_id}", 500

@app.route('/search_page', methods=['GET'])
def search_page():
    return render_template('search.html')

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')

    if not query:
        return "Please provide a search query."
    
    # Call movie and TV search APIs
    results_tv = search_tv_show(query)  # Your current function
    results_movie = search_movie(query)  # Your current function
    
    # Add 'media_type' to each result so we can differentiate between movie and tv
    for item in results_tv:
        item['media_type'] = 'tv'
    for item in results_movie:
        item['media_type'] = 'movie'
    # Combine both lists of results
    results = results_tv + results_movie

    # Return the search results with the 'category' as context
    return render_template("search_results.html", query = query, results=results)

if __name__ == '__main__':
    app.run(debug=True)