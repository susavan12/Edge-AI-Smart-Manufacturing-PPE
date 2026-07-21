// ======================================
// Elements
// ======================================

const violations = document.getElementById("violations");

const video = document.getElementById("video");
const result = document.getElementById("result");

const status = document.getElementById("status");
const person = document.getElementById("person");
const hardhat = document.getElementById("hardhat");
const no_hardhat = document.getElementById("no_hardhat");
const vest = document.getElementById("vest");
const no_vest = document.getElementById("no_vest");

// Alarm
const alarm = document.getElementById("alarm");

const cameraStatus = document.getElementById("cameraStatus");

const startBtn = document.getElementById("startBtn");

const stopBtn = document.getElementById("stopBtn");

// ======================================
// Variables
// ======================================

let stream = null;
let intervalId = null;
let violationInterval = null;
let cameraStarted = false;
let isProcessing = false;
let alarmRunning = false;

// ======================================
// Start Camera
// ======================================

async function startCamera() {

    if (cameraStarted) return;

    try {

        stream = await navigator.mediaDevices.getUserMedia({

            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                frameRate: { ideal: 30, max: 30 }
            },

            audio: false

        });

        video.srcObject = stream;
        await video.play();

        cameraStarted = true;

        cameraStatus.innerHTML = "🟢 Camera LIVE";
        cameraStatus.className = "badge bg-success";

        startBtn.disabled = true;
        stopBtn.disabled = false;

        clearInterval(intervalId);

        // Capture a frame every 450 ms
        intervalId = setInterval(sendFrame, 450);

        loadViolations();

        clearInterval(violationInterval);

        violationInterval = setInterval(loadViolations, 5000);

    }

    catch(error){

        console.log(error);

        alert(error.message);

    }

}

// ======================================
// Send Frame
// ======================================

async function sendFrame() {

    if (!cameraStarted) return;

    if (video.readyState !== 4) return;

    if (isProcessing) return;

    isProcessing = true;

    try {

        // ======================================
        // Capture Current Frame
        // ======================================

        const canvas = document.createElement("canvas");

        canvas.width = 640;
        canvas.height = 480;

        const ctx = canvas.getContext("2d");

        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        const image = canvas.toDataURL("image/jpeg", 0.70);

        // ======================================
        // Send Frame to Flask
        // ======================================

        const response = await fetch("/detect", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                image: image
            })

        });

        if (!response.ok) {

            throw new Error("Server Error");

        }

        const data = await response.json();

        if (!cameraStarted) return;

        // ======================================
        // Update Detection Image
        // ======================================

        if (data.image && data.image.startsWith("data:image")) {

            result.src = data.image;

        }

        // ======================================
        // Update Dashboard
        // ======================================

        status.innerHTML = data.status || "NO PERSON";

        person.innerHTML = data.person || 0;

        hardhat.innerHTML = data.hardhat || 0;

        no_hardhat.innerHTML = data.no_hardhat || 0;

        vest.innerHTML = data.vest || 0;

        no_vest.innerHTML = data.no_vest || 0;

        violations.innerHTML = data.violations || 0;

        // ======================================
        // Status Color + Alarm
        // ======================================

        status.style.fontWeight = "bold";

        // ---------- UNSAFE ----------
        if (data.status === "UNSAFE" && data.person > 0) {

            status.style.background = "#dc3545";
            status.style.color = "white";

            if (!alarmRunning) {

                alarmRunning = true;

                alarm.currentTime = 0;

                alarm.play().catch(err => {

                    console.log("Alarm:", err);

                });

            }

        }

        // ---------- SAFE ----------
        else if (data.status === "SAFE" && data.person > 0) {

            status.style.background = "#198754";
            status.style.color = "white";

            if (alarmRunning) {

                alarm.pause();

                alarm.currentTime = 0;

                alarmRunning = false;

            }

        }

        // ---------- NO PERSON ----------
        else {

            status.style.background = "#ffc107";
            status.style.color = "black";

            status.innerHTML = "NO PERSON";

            if (alarmRunning) {

                alarm.pause();

                alarm.currentTime = 0;

                alarmRunning = false;

            }

        }

    }

    catch (error) {

        console.error("Detection Error:", error);

    }

    finally {

        isProcessing = false;

    }

}

// ======================================
// Stop Camera
// ======================================

function stopCamera() {

    cameraStarted = false;

    isProcessing = false;

    clearInterval(intervalId);

    clearInterval(violationInterval);

    if (stream) {

        stream.getTracks().forEach(track => track.stop());

    }

    stream = null;

    if (alarm) {

        alarm.pause();
        alarm.currentTime = 0;

    }

    alarmRunning = false;

    video.srcObject = null;

    result.removeAttribute("src");

    cameraStatus.innerHTML = "⚫ Camera OFF";
    cameraStatus.className = "badge bg-secondary";

    startBtn.disabled = false;
    stopBtn.disabled = true;

}

// ======================================
// Load Violation List
// ======================================

// ======================================
// Load Violation List
// ======================================

async function loadViolations() {

    try {

        const response = await fetch("/get_violations");

        if (!response.ok) {

            throw new Error("Unable to load violations.");

        }

        const data = await response.json();

        let html = "";

        if (data.length === 0) {

            html = `

            <div class="empty-box">

                <img src="/static/icons/shield.png" width="70">

                <h5>No Violations</h5>

                <p>System is continuously monitoring the workplace.</p>

            </div>

            `;

        }

        else {

            data.forEach(function(item) {

                html += `

                <div class="violation-card">

                    <img src="${item.path}" alt="Violation Image">

                    <div class="violation-info">

                        <div class="violation-title">

                            🚨 PPE Violation Detected

                        </div>

                        <div>

                            ${item.name}

                        </div>

                        <div class="violation-time">

                            ${new Date().toLocaleString()}

                        </div>

                    </div>

                </div>

                `;

            });

        }

        document.getElementById("violation_list").innerHTML = html;

    }

    catch(error){

        console.error("Violation Error:", error);

    }

}

window.onload = function () {

    stopBtn.disabled = true;

    startBtn.disabled = false;

    result.removeAttribute("src");

}