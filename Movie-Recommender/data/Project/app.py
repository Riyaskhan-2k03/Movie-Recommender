import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
import requests
import numpy as np
import cv2

from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_cors import CORS
from deepface import DeepFace
from movie_recommender import fetch_movies_for_emotion, fetch_tmdb_movies_by_ids
from dotenv import load_dotenv
from werkzeug.datastructures import FileStorage

# Load .env
load_dotenv()

PORT = int(os.getenv("PORT", 5000))
RECOMMENDER_API_URL = os.getenv("RECOMMENDER_API_URL", "").strip() or None

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp"}

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "change-me")
CORS(app)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def detect_emotion_from_webcam(timeout_frames=30):
    """
    Capture frames from server webcam and run DeepFace.analyze until we detect an emotion
    or reach timeout_frames. Returns a lowercase emotion string (e.g. 'happy', 'sad').
    """
    cap = cv2.VideoCapture(0)
    emotion = "neutral"

    if not cap.isOpened():
        app.logger.warning("Webcam not available")
        return emotion

    frames_checked = 0
    while frames_checked < timeout_frames:
        ret, frame = cap.read()
        frames_checked += 1
        if not ret or frame is None:
            continue

        try:
            resp = DeepFace.analyze(frame, actions=["emotion"], enforce_detection=False)
            if isinstance(resp, list) and len(resp) > 0:
                resp = resp[0]
            dominant = resp.get("dominant_emotion") if isinstance(resp, dict) else None
            if dominant:
                emotion = dominant.lower()
                break
        except Exception as e:
            app.logger.debug(f"DeepFace analyze error (webcam): {e}")
            continue

    cap.release()
    return emotion


def detect_emotion_from_image_file(file_storage: FileStorage):
    """
    Read uploaded image bytes, decode to OpenCV image and run DeepFace.analyze.
    Returns a lowercase emotion string or 'neutral' on failure.
    """
    emotion = "neutral"
    try:
        data = file_storage.read()
        # Reset stream so Flask/Werkzeug can potentially save or re-read later
        try:
            file_storage.stream.seek(0)
        except Exception:
            pass

        if not data:
            return emotion

        nparr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            app.logger.debug("Uploaded file could not be decoded as image by OpenCV.")
            return emotion

        resp = DeepFace.analyze(img, actions=["emotion"], enforce_detection=False)
        if isinstance(resp, list) and len(resp) > 0:
            resp = resp[0]
        dominant = resp.get("dominant_emotion") if isinstance(resp, dict) else None
        if dominant:
            emotion = dominant.lower()
    except Exception as e:
        app.logger.debug(f"DeepFace analyze error (upload): {e}")
    return emotion


def call_external_recommender(emotion):
    """
    Call external recommender if configured. Accepts emotion string and returns:
      - dict{"movies": [...] } OR
      - dict{"ids": [...] } OR
      - None on failure/not-configured.
    Supported response shapes (examples):
      - {"recommended_ids": [123, 234]}
      - {"movies": [{title, overview, poster, release_date, tmdb_id}, ...]}
      - [123, 234]
      - [{"id": 123, "title": ...}, ...]
    """
    if not RECOMMENDER_API_URL:
        return None

    try:
        resp = requests.post(RECOMMENDER_API_URL, json={"emotion": emotion}, timeout=6)
        resp.raise_for_status()
        data = resp.json()

        # dict variants
        if isinstance(data, dict):
            # common: recommended_ids
            if "recommended_ids" in data and isinstance(data["recommended_ids"], list):
                return {"ids": data["recommended_ids"]}
            if "ids" in data and isinstance(data["ids"], list):
                return {"ids": data["ids"]}
            if "movies" in data and isinstance(data["movies"], list):
                return {"movies": data["movies"]}
            if "results" in data and isinstance(data["results"], list):
                results = data["results"]
                if results and isinstance(results[0], dict) and "id" in results[0]:
                    return {"movies": results}
                if results and isinstance(results[0], (int, str)):
                    return {"ids": results}
        # list variants
        if isinstance(data, list):
            if len(data) == 0:
                return {"ids": []}
            first = data[0]
            if isinstance(first, dict) and ("id" in first or "tmdb_id" in first):
                movies = []
                for item in data:
                    mid = item.get("id") or item.get("tmdb_id")
                    movies.append({
                        "title": item.get("title") or item.get("name"),
                        "overview": item.get("overview"),
                        "poster": item.get("poster") or item.get("poster_path"),
                        "release_date": item.get("release_date") or item.get("first_air_date"),
                        "tmdb_id": mid,
                    })
                return {"movies": movies}
            if isinstance(first, (int, str)):
                return {"ids": data}
    except Exception:
        app.logger.exception("External recommender call failed")
    return None


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/recommend", methods=["GET", "POST"])
def recommend():
    if request.method == "GET":
        return render_template("recommend.html")

    # POST: receive either uploaded image or choose webcam
    source = request.form.get("source", "upload")
    emotion = "neutral"

    if source == "webcam":
        emotion = detect_emotion_from_webcam()
    else:
        # 'upload' or 'client' or anything else treated as upload
        file = request.files.get("image")
        if not file:
            flash("No file uploaded. You can also choose 'Use server webcam' if available.", "error")
            return redirect(url_for("recommend"))
        if file.filename == "":
            flash("No file selected.", "error")
            return redirect(url_for("recommend"))
        if not allowed_file(file.filename):
            flash(f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}", "error")
            return redirect(url_for("recommend"))
        emotion = detect_emotion_from_image_file(file)

    recommended = []

    # Try external recommender first (if configured)
    recommender_resp = call_external_recommender(emotion) if RECOMMENDER_API_URL else None
    if recommender_resp:
        if "movies" in recommender_resp:
            recommended = recommender_resp["movies"]
        elif "ids" in recommender_resp and recommender_resp["ids"]:
            try:
                recommended = fetch_tmdb_movies_by_ids(recommender_resp["ids"])
            except Exception:
                app.logger.exception("Failed to fetch movies for recommender ids")
                recommended = []

    # Fallback to built-in TMDb-by-emotion if we still have no results
    if not recommended:
        try:
            recommended = fetch_movies_for_emotion(emotion)
        except Exception:
            app.logger.exception("Failed to fetch movies from TMDb")
            return jsonify({"error": "Failed to fetch recommendations"}), 500

    return render_template("results.html", mood=emotion, recommendations=recommended)


@app.route("/api/recommend", methods=["GET"])
def api_recommend():
    """
    API-only endpoint that uses server webcam to detect emotion and returns JSON.
    Good for headless use / programmatic calls.
    """
    emotion = detect_emotion_from_webcam()
    try:
        movies = fetch_movies_for_emotion(emotion)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"mood": emotion, "recommendations": movies})


if __name__ == "__main__":
    debug = os.getenv("FLASK_ENV", "production") == "development"
    app.run(host="0.0.0.0", port=PORT, debug=debug)