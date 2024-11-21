from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from config import Config, DevelopmentConfig, TestingConfig, ProductionConfig
from tmdb_search import search_movie, search_tv_show
from models import db, Users, Favorite, Comment
import requests
from dotenv import load_dotenv
load_dotenv()
import os

app = Flask(__name__)

app.config.from_object(Config)

tmdb_api_key = os.getenv("TMDB_API_KEY")
tmdb_img_url = app.config['TMDB_IMAGE_BASE_URL']
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.config['STATIC_FOLDER'], 'favicon.ico', mimetype='image/vnd.microsoft.icon')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = app.route('/login', methods=["GET", "POST"])
login_manager.login_message = "Please log in to access this page."

with app.app_context():   
    db.init_app(app)
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
        login_user(user)
        return redirect(url_for("home"))
    return render_template("register.html")
 
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = Users.query.filter_by(
            username=request.form.get("username")).first()
        if user.password == request.form.get("password"):
            login_user(user)
            return redirect(url_for('home'))
    return render_template("login.html")
 
@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))

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

        if file and Config.allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            base, ext = os.path.splitext(original_filename)
            final_filename = original_filename
            final_file_path = os.path.join(app.config['UPLOAD_FOLDER'], final_filename)

            counter = 1
            while os.path.exists(final_file_path):
                final_filename = f"{base}({counter}){ext}"
                final_file_path = os.path.join(app.config['UPLOAD_FOLDER'], final_filename)
                counter += 1

        current_user.profile_picture = final_filename

        file.save(final_file_path)
        db.session.commit()

        pic_path = current_user.profile_picture
        print("Uploaded file path: ", pic_path)

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
@login_required
def home():
    return render_template("about_us.html")

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

    total_genres = total_tv_genres | total_movie_genres

    # Fetch recommended movies based on collected genre IDs
    recommended_movies = []
    genre_query = ','.join(map(str, total_genres))
    movie_rec_url = f"https://api.themoviedb.org/3/discover/movie?api_key={tmdb_api_key}&with_genre_ids={genre_query}&sort_by=popularity.desc"
    try:
        response = requests.get(movie_rec_url)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        recommended_movies = response.json().get('results', [])
        if not recommended_movies:
            print("No movies found for the given genres.")
        else:
            print(f"Found {len(recommended_movies)} recommended movies.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching movie recommendations: {e}")

    # Fetch recommended TV shows based on collected genre IDs
    recommended_tv_shows = []
    genre_query = ','.join(map(str, total_genres))
    tv_rec_url = f"https://api.themoviedb.org/3/discover/tv?api_key={tmdb_api_key}&with_genre_ids={genre_query}&sort_by=popularity.desc"
    try:
        response = requests.get(tv_rec_url)
        response.raise_for_status()
        recommended_tv_shows = response.json().get('results', [])
        if not recommended_tv_shows:
            print("No TV shows found for the given genres.")
        else:
            print(f"Found {len(recommended_tv_shows)} recommended TV shows.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching TV show recommendations: {e}")

    # Render recommendations in the template
    return render_template('for_you.html', movie_recs = recommended_movies, tv_recs = recommended_tv_shows)

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

    if not total_favorites:
        return render_template('favorites_empty.html')
    else:
        return render_template('favorites.html', faves=total_favorites)

@app.route('/favorite', methods=['POST'])
@login_required  # Ensure user is logged in
def add_to_favorites():
    media_type = request.form.get('media_type')  # 'movie' or 'tv'
    media_id = request.form.get('media_id')
    # Add the new favorite
    favorite = Favorite(
        movie_id=media_id if media_type == 'movie' else None,
        tv_id=media_id if media_type == 'tv' else None,
        user_id=current_user.id
    )
    db.session.add(favorite)
    db.session.commit()
    flash('Added to favorites!', 'success')

    return redirect(request.referrer or url_for("favorites"))

@app.route('/remove_favorite/<int:fav_id>', methods=['POST'])
@login_required  # Ensure user is logged in
def remove_from_favorites(fav_id):
    favorite = Favorite.query.get_or_404(fav_id)

    if favorite and favorite.user_id == current_user.id:
        db.session.delete(favorite)
        db.session.commit()
        flash('Removed from favorites!', 'success')
    else:
        flash('Error, item not found or unauthorized.', 'danger')

    return redirect(url_for('favorites'))  # Redirect to favorites page

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
@login_required
def popular_movies_and_tvshows():
    # Popular Movies
    movie_url = f"https://api.themoviedb.org/3/movie/popular?api_key={tmdb_api_key}"
    movie_response = requests.get(movie_url)
    
    if movie_response.status_code == 200:
        movie_data = movie_response.json()
        for movie in movie_data['results']:
            if movie['poster_path']:
                movie['poster_url'] = f"{tmdb_img_url}w500{movie['poster_path']}"
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
                tv['poster_url'] = f"{tmdb_img_url}w500{tv['poster_path']}"
            else:
                tv['poster_url'] = "https://via.placeholder.com/500x750?text=No+Image"
    else:
        return "Unable to fetch popular tv shows", tv_response.status_code  

    # Render the combined template and pass both movie and tv data
    return render_template("explore.html", movies=movie_data['results'], tvs=tv_data['results'])

@app.route('/movie/review/<int:movie_id>', methods=['GET', 'POST'])
@login_required
def movie_reviews(movie_id):
    reviews_url = f"https://api.themoviedb.org/3/movie/{movie_id}/reviews?api_key={tmdb_api_key}"
    details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={tmdb_api_key}"

    is_favorite = Favorite.query.filter_by(user_id=current_user.id, movie_id=movie_id).first() is not None
    print(is_favorite)

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
        print(movie_details)
        poster_url = f"{tmdb_img_url}w500{movie_details['poster_path']}" if movie_details.get('poster_path') else "https://via.placeholder.com/500x750?text=No+Image"

        return render_template(
            "movie_review.html",
            tmdb_reviews=tmdb_reviews,
            user_comments=user_comments,
            movie=movie_details,
            poster_url=poster_url,
            is_favorite=is_favorite
        )
    else:
        return f"Unable to fetch reviews or details for movie {movie_id}", 500

@app.route('/tv/review/<int:tv_id>', methods=['GET', 'POST'])
@login_required
def tv_reviews(tv_id):
    reviews_url = f"https://api.themoviedb.org/3/tv/{tv_id}/reviews?api_key={tmdb_api_key}"
    details_url = f"https://api.themoviedb.org/3/tv/{tv_id}?api_key={tmdb_api_key}"

    is_favorite = Favorite.query.filter_by(user_id=current_user.id, tv_id=tv_id).first() is not None

    print(is_favorite)
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

        poster_url = f"{tmdb_img_url}w500{tv_details['poster_path']}" if tv_details.get('poster_path') else "https://via.placeholder.com/500x750?text=No+Image"

        return render_template(
            "tv_review.html",
            tmdb_reviews=tmdb_reviews,
            user_comments=user_comments,
            tv=tv_details,
            poster_url=poster_url,
            is_favorite=is_favorite
        )
    else:
        return f"Unable to fetch reviews or details for TV show {tv_id}", 500

@app.route('/search_page', methods=['GET'])
@login_required
def search_page():
    return render_template('search.html')

@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('query')

    if not query:
        return "Please provide a search query."

    results_tv = search_tv_show(query)  
    results_movie = search_movie(query)  

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