import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
import requests

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_URL = "https://api.themoviedb.org/3"

EMOTION_GENRE_MAP = {
    "happy": ["Comedy", "Romance", "Adventure"],
    "sad": ["Family", "Animation", "Drama"],
    "angry": ["Action", "Thriller"],
    "neutral": ["Drama", "Mystery"],
    "surprise": ["Sci-Fi", "Fantasy"],
    "fear": ["Horror", "Thriller"],
    "default": ["Drama"],
}


def fetch_movies_for_emotion(emotion, max_per_genre=3):
    """
    Simple TMDb search: performs a search/movie query using genre words.
    """
    if not TMDB_API_KEY:
        print("Warning: TMDB_API_KEY not set in environment. Movie recommendations will be disabled.")
        return []

    key = emotion.lower() if emotion and emotion.lower() in EMOTION_GENRE_MAP else "default"
    genres = EMOTION_GENRE_MAP.get(key, EMOTION_GENRE_MAP["default"])[:3]

    results = []
    for g in genres:
        url = f"{TMDB_URL}/search/movie"
        params = {"api_key": TMDB_API_KEY, "query": g, "page": 1}
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            items = data.get("results", [])[:max_per_genre]
            for m in items:
                results.append(
                    {
                        "title": m.get("title"),
                        "overview": m.get("overview"),
                        "poster": f"https://image.tmdb.org/t/p/w500{m.get('poster_path')}" if m.get("poster_path") else None,
                        "release_date": m.get("release_date"),
                        "tmdb_id": m.get("id"),
                    }
                )
        except Exception as e:
            # print to server logs but continue
            print(f"Error fetching for genre {g}: {e}")

    # Deduplicate by tmdb_id
    seen = set()
    deduped = []
    for m in results:
        tid = m.get("tmdb_id")
        if tid and tid not in seen:
            seen.add(tid)
            deduped.append(m)

    return deduped


def fetch_tmdb_movies_by_ids(ids):
    """
    Given a list of TMDB ids (ints or strings), 
    fetch movie details for each and return
    in the same simple dict format used above.
    
    """
    if not TMDB_API_KEY:
        print("Warning: TMDB_API_KEY not set in environment. Movie recommendations will be disabled.")
        return []
    results = []
    for mid in ids:
        try:
            url = f"{TMDB_URL}/movie/{mid}"
            params = {"api_key": TMDB_API_KEY}
            r = requests.get(url, params=params, timeout=8)
            r.raise_for_status()
            m = r.json()
            results.append(
                {
                    "title": m.get("title"),
                    "overview": m.get("overview"),
                    "poster": f"https://image.tmdb.org/t/p/w500{m.get('poster_path')}" if m.get("poster_path") else None,
                    "release_date": m.get("release_date"),
                    "tmdb_id": m.get("id"),
                }
            )
        except Exception as e:
            # log and continue; missing ids won't stop everything
            print(f"Error fetching movie id {mid}: {e}")
    return results