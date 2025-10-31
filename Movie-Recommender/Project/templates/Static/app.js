const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const captureBtn = document.getElementById("captureBtn");
const status = document.getElementById("status");
const result = document.getElementById("result");

async function initCam() {
    let stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;
}
initCam();

captureBtn.onclick = async () => {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    canvas.getContext("2d").drawImage(video, 0, 0);
    let imageBase64 = canvas.toDataURL("image/png");

    status.innerText = "Analyzing mood...";

    let res = await fetch("/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json"},
        body: JSON.stringify({ image: imageBase64 })
    });

    let data = await res.json();
    
    if(data.mood) {
        status.innerText = "Mood: " + data.mood;
        displayMovies(data.recommendations);
    } else {
        status.innerText = "Error detecting emotion";
    }
};

function displayMovies(list) {
    if(!list?.length){
        result.innerHTML = "<p>No movies found.</p>";
        return;
    }

    let html = "";
    list.forEach(m => {
        html += `
        <div class="movie">
            <img src="${m.poster}" width="120">
            <div>
                <h3>${m.title}</h3>
                <p>${m.overview}</p>
            </div>
        </div>`;
    });
    result.innerHTML = html;
}
