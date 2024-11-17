import os
import requests
from dotenv import load_dotenv

load_dotenv()

tmdb_api_key = os.getenv("TMDB_API_KEY")
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"

def search_movie(title):
    """Search for a movie by title on TMDb."""
    url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={title}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        for movie in data['results']:
            if movie['poster_path']:
                movie['poster_url'] = f"{TMDB_IMAGE_BASE_URL}w500{movie['poster_path']}"
            else:
                movie['poster_url'] = "https://via.placeholder.com/500x750?text=No+Image"
        return data['results']
    else:
        print("Error fetching movie data:", response.status_code)
        return None

def search_tv_show(title):
    """Search for a TV show by title on TMDb."""
    url = f"https://api.themoviedb.org/3/search/tv?api_key={tmdb_api_key}&query={title}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        for show in data['results']:
            if show['poster_path']:
                show['poster_url'] = f"{TMDB_IMAGE_BASE_URL}w500{show['poster_path']}"
            else:
                show['poster_url'] = "https://via.placeholder.com/500x750?text=No+Image"
        return data['results']
    else:
        print("Error fetching TV show data:", response.status_code)
        return None