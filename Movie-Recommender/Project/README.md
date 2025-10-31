# MoodFlix - Backend (Flask)

## Quick start (local)

1. Create and activate a virtual environment (recommended)

   ```sh
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   ```

2. Install dependencies

   ```sh
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in your TMDB_API_KEY

4. Run the Flask app

   ```sh
   python app.py
   ```

5. Open your browser and visit: [http://127.0.0.1:5000/recommend](http://127.0.0.1:5000/recommend)

The endpoint will attempt to access your default webcam, capture a frame, analyze emotion, and return movie recommendations from TMDb.

## Notes & Troubleshooting
- If DeepFace fails due to missing system libs or model downloads, run the server once with internet access so DeepFace can pull required models. DeepFace caches models locally.
- If you prefer not to use a webcam or you're running in a remote server, you can modify `detect_emotion_from_webcam` to accept an uploaded image (from frontend) and run DeepFace.analyze on that image instead.