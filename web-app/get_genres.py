import requests
from dotenv import load_dotenv
import os 

load_dotenv()
tmdb_api_key = os.getenv("TMDB_API_KEY")

def fetch_genres():
    movie_genres = []
    tv_genres = []
    
    # Fetch movie genres
    movie_genre_url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={tmdb_api_key}&language=en-US"
    movie_genres_response = requests.get(movie_genre_url)
    if movie_genres_response.status_code == 200:
        movie_genres = movie_genres_response.json().get('genres', [])
    
    # Fetch TV genres
    tv_genre_url = f"https://api.themoviedb.org/3/genre/tv/list?api_key={tmdb_api_key}&language=en-US"
    tv_genres_response = requests.get(tv_genre_url)
    if tv_genres_response.status_code == 200:
        tv_genres = tv_genres_response.json().get('genres', [])
    
    return movie_genres, tv_genres
