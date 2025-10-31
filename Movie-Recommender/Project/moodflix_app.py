import os, base64, io
from flask import Flask, request, jsonify, render_template_string
from PIL import Image
from dotenv import load_dotenv
from movie_recommender import fetch_movies_for_emotion

try:
    from deepface import DeepFace
except:
    DeepFace = None

load_dotenv()
app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>MoodFlix AI</title>
<style>
body {font-family:Arial;background:#f1f1f1;padding:20px;text-align:center;}
.container {background:#fff;padding:20px;border-radius:10px;max-width:700px;margin:auto;}
video {width:100%;border-radius:10px;margin-bottom:10px;}
button {padding:12px 20px;font-size:16px;background:black;color:white;border:none;border-radius:8px;cursor:pointer;}
.movie {display:flex;gap:10px;margin:15px 0;}
</style>
</head>
<body>

<div class="container">
<h1>MoodFlix 🎬</h1>
<p>AI reads your face & recommends movies</p>

<video id="video" autoplay></video>
<canvas id="canvas" style="display:none;"></canvas>

<button id="captureBtn">Capture Mood</button>
<p id="status"></p>
<div id="result"></div>
</div>

<script>
const video=document.getElementById("video");
const canvas=document.getElementById("canvas");
const btn=document.getElementById("captureBtn");
const status=document.getElementById("status");
const result=document.getElementById("result");

navigator.mediaDevices.getUserMedia({video:true})
.then(stream=>video.srcObject=stream);

btn.onclick=async()=>{
canvas.width=video.videoWidth;canvas.height=video.videoHeight;
canvas.getContext("2d").drawImage(video,0,0);
let img=canvas.toDataURL("image/png");
status.innerText="Analyzing mood...";

let res=await fetch("/analyze",{method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({image:img})});
let data=await res.json();

if(data.mood){
status.innerText="Mood: "+data.mood;
result.innerHTML=data.recommendations.map(m=>`
<div class="movie">
<img src="${m.poster}" width="120">
<div><h3>${m.title}</h3><p>${m.overview}</p></div>
</div>`).join("")
}else{
status.innerText="Error detecting mood";
}
}
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_PAGE)

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        img_data = request.json["image"].split(",")[1]
        img = Image.open(io.BytesIO(base64.b64decode(img_data))).convert("RGB")
        
        emotion = "neutral"
        if DeepFace:
            import numpy as np
            arr = np.array(img)[:, :, ::-1]
            res = DeepFace.analyze(arr, actions=['emotion'], enforce_detection=False)
            emotion = res[0]["dominant_emotion"].lower()

        movies = fetch_movies_for_emotion(emotion)
        return jsonify({"mood": emotion, "recommendations": movies})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
