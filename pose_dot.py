"""Streamlit-hosted, browser-side elbow angle tracker.

Deploy on Streamlit Community Cloud with this file as the entrypoint.
The webcam and MediaPipe pose detection run in the visitor's browser, not
on the server. This avoids WebRTC relay/TURN configuration.
"""

import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(
    page_title="Elbow Angle Tracker",
    page_icon="📐",
    layout="centered",
)

st.title("Elbow Angle Tracker")
st.write(
    "Start your camera, stand far enough back to show your right arm, "
    "and watch the elbow angle update live."
)

HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/pose/pose.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 0;
      background: transparent;
      color: #f4f6f8;
      font: 15px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .controls { display: flex; flex-wrap: wrap; gap: 10px; margin: 8px 0 14px; }
    button {
      border: 0; border-radius: 10px; padding: 11px 17px;
      font: 700 14px system-ui, sans-serif; cursor: pointer;
    }
    #start { background: #73e2a7; color: #10251a; }
    #stop { background: #303744; color: #f4f6f8; }
    button:disabled { opacity: .45; cursor: not-allowed; }
    .stage {
      width: 100%; background: #080a0d; border: 1px solid #303744;
      border-radius: 12px; overflow: hidden;
    }
    canvas { display: block; width: 100%; height: auto; }
    .metrics {
      display: flex; align-items: baseline; gap: 12px;
      flex-wrap: wrap; padding: 10px 0 0;
    }
    #angle { font-size: 42px; line-height: 1.2; font-weight: 800; color: #73e2a7; }
    #status { margin: 8px 0 0; min-height: 2.7em; color: #c0c7d1; line-height: 1.4; }
    .privacy { font-size: 12px; color: #969eaa; line-height: 1.4; }
  </style>
</head>
<body>
  <div class="controls">
    <button id="start" type="button">Start camera</button>
    <button id="stop" type="button" disabled>Stop camera</button>
  </div>
  <div class="stage"><canvas id="canvas" width="640" height="480"></canvas></div>
  <div class="metrics">
    <span id="angle">--°</span>
    <span>Right elbow angle</span>
  </div>
  <p id="status" role="status">Camera is off. Press Start camera to begin.</p>
  <p class="privacy">Privacy: video is processed in this browser and is not sent to the Python app. Camera access requires permission.</p>

<script>
(function () {
  const video = document.createElement('video');
  video.playsInline = true;
  video.muted = true;

  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d');
  const angleOutput = document.getElementById('angle');
  const status = document.getElementById('status');
  const startButton = document.getElementById('start');
  const stopButton = document.getElementById('stop');

  let stream = null;
  let pose = null;
  let running = false;
  let busy = false;
  let animationId = null;

  function angleBetween(a, b, c) {
    const baX = a.x - b.x, baY = a.y - b.y;
    const bcX = c.x - b.x, bcY = c.y - b.y;
    const denominator = Math.hypot(baX, baY) * Math.hypot(bcX, bcY);
    if (denominator < 1e-8) return null;
    const cosine = Math.max(-1, Math.min(1,
      (baX * bcX + baY * bcY) / denominator));
    return Math.acos(cosine) * 180 / Math.PI;
  }

  function showStatus(message) {
    status.textContent = message;
  }

  function onResults(results) {
    if (!running) return;

    const width = video.videoWidth || 640;
    const height = video.videoHeight || 480;
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    ctx.clearRect(0, 0, width, height);

    if (!results.poseLandmarks) {
      angleOutput.textContent = '--°';
      showStatus('No pose detected yet. Move back so your upper body and arm are visible.');
      return;
    }

    ctx.drawImage(results.image, 0, 0, width, height);
    drawConnectors(ctx, results.poseLandmarks, POSE_CONNECTIONS,
      {color: '#73e2a7', lineWidth: 4});
    drawLandmarks(ctx, results.poseLandmarks,
      {color: '#ffcf5a', lineWidth: 2, radius: 4});

    const points = results.poseLandmarks;
    // MediaPipe Pose indices: right shoulder 12, right elbow 14, right wrist 16.
    const shoulder = points[12];
    const elbow = points[14];
    const wrist = points[16];
    const visible = shoulder.visibility > 0.45 &&
                    elbow.visibility > 0.45 &&
                    wrist.visibility > 0.45;
    const angle = visible ? angleBetween(shoulder, elbow, wrist) : null;

    if (angle === null) {
      angleOutput.textContent = '--°';
      showStatus('Keep your right shoulder, elbow, and wrist in the camera view.');
      return;
    }

    angleOutput.textContent = angle.toFixed(1) + '°';
    showStatus('Tracking your right arm live.');
    ctx.fillStyle = '#73e2a7';
    ctx.font = 'bold 28px system-ui, sans-serif';
    ctx.fillText(angle.toFixed(1) + '°', 18, 36);
  }

  async function processFrame() {
    if (!running || busy) return;
    if (video.readyState >= 2 && pose) {
      busy = true;
      try {
        await pose.send({image: video});
      } catch (error) {
        showStatus('Pose processing failed: ' + error.message);
      } finally {
        busy = false;
      }
    }
    if (running) animationId = requestAnimationFrame(processFrame);
  }

  async function stopCamera() {
    running = false;
    if (animationId !== null) cancelAnimationFrame(animationId);
    animationId = null;
    if (stream) stream.getTracks().forEach(function (track) { track.stop(); });
    stream = null;
    video.srcObject = null;
    if (pose) {
      try { await pose.close(); } catch (_) {}
      pose = null;
    }
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    angleOutput.textContent = '--°';
    startButton.disabled = false;
    stopButton.disabled = true;
    showStatus('Camera is off.');
  }

  startButton.addEventListener('click', async function () {
    startButton.disabled = true;
    showStatus('Requesting camera permission…');

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera API unavailable. Open the HTTPS Streamlit app in a supported browser.');
      }
      if (typeof Pose === 'undefined' ||
          typeof drawConnectors === 'undefined' ||
          typeof drawLandmarks === 'undefined') {
        throw new Error('Pose scripts did not load. Refresh the page and check your internet connection.');
      }

      stream = await navigator.mediaDevices.getUserMedia({
        video: {facingMode: 'user', width: {ideal: 640}, height: {ideal: 480}},
        audio: false
      });
      video.srcObject = stream;
      await video.play();

      pose = new Pose({
        locateFile: function (file) {
          return 'https://cdn.jsdelivr.net/npm/@mediapipe/pose/' + file;
        }
      });
      pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });
      pose.onResults(onResults);

      running = true;
      stopButton.disabled = false;
      showStatus('Camera started. Loading the pose model…');
      animationId = requestAnimationFrame(processFrame);
    } catch (error) {
      if (stream) stream.getTracks().forEach(function (track) { track.stop(); });
      stream = null;
      video.srcObject = null;
      startButton.disabled = false;
      stopButton.disabled = true;
      showStatus('Could not start camera: ' + error.message +
        ' Check browser camera permissions, then refresh and try again.');
    }
  });

  stopButton.addEventListener('click', stopCamera);
  window.addEventListener('pagehide', function () {
    running = false;
    if (stream) stream.getTracks().forEach(function (track) { track.stop(); });
  });
})();
</script>
</body>
</html>
"""

components.html(HTML, height=730, scrolling=False)

with st.expander("How it works"):
    st.write(
        "The camera and pose model run in your browser. The app calculates the "
        "angle at your right elbow using the shoulder, elbow, and wrist landmarks. "
        "No TURN server or video relay is needed."
    )
