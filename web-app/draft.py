class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # "movie" or "tv"
    tmdb_id = db.Column(db.Integer, nullable=False)  # Unique ID from TMDb
    poster_url = db.Column(db.String(300))  # URL to the poster image

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

favorites = db.relationship('Favorite', backref='user', lazy=True)\




<h1>{{ tv['name'] }} ({{ tv['first_air_date'][:4] }})</h1>
    <img src="{{ poster_url }}" alt="Poster for {{ tv['name'] }}" style="width:200px;">
    <p><strong>Overview:</strong> {{ tv['overview'] }}</p>