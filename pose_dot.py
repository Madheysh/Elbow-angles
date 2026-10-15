"""Browser-based elbow-angle demo.

Run with: python pose_dot.py
Open the Replit web preview. The visitor's webcam and pose detection run in
their browser; the Python server only serves this page.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import os


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Elbow Angle Tracker</title>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/pose/pose.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
  <style>
    :root { color-scheme: dark; font-family: system-ui, sans-serif; }
    body { margin: 0; padding: 24px; background: #101318; color: #f4f6f8; }
    main { max-width: 900px; margin: auto; }
    h1 { margin: 0 0 8px; font-size: clamp(1.5rem, 4vw, 2.2rem); }
    p { color: #b8c0cc; }
    .controls { display: flex; gap: 10px; flex-wrap: wrap; margin: 18px 0; }
    button { border: 0; border-radius: 9px; padding: 11px 16px; font-weight: 700; cursor: pointer; }
    #start { background: #65e6a5; color: #10251a; }
    #stop { background: #303744; color: white; }
    .stage { background: #050608; border: 1px solid #303744; border-radius: 14px; overflow: hidden; }
    canvas { display: block; width: 100%; height: auto; }
    .readout { display: flex; align-items: baseline; gap: 12px; margin-top: 16px; }
    #angle { font-size: 2.5rem; font-weight: 800; color: #65e6a5; }
    #status { min-height: 1.5em; color: #b8c0cc; }
    .note { font-size: .9rem; }
  </style>
</head>
<body>
<main>
  <h1>Elbow Angle Tracker</h1>
  <p>Allow camera access, then stand where your right shoulder, elbow, and wrist are visible.</p>
  <div class="controls">
    <button id="start">Start camera</button>
    <button id="stop" disabled>Stop camera</button>
  </div>
  <div class="stage"><canvas id="canvas" width="640" height="480"></canvas></div>
  <div class="readout"><span id="angle">--°</span><span>Right elbow angle</span></div>
  <div id="status" role="status">Camera is off.</div>
  <p class="note">Camera video is processed in your browser; it is not uploaded to this Python server. Requires HTTPS and camera permission.</p>
</main>
<script>
(() => {
  const video = document.createElement('video');
  video.playsInline = true;
  video.muted = true;
  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d');
  const angleLabel = document.getElementById('angle');
  const status = document.getElementById('status');
  const startButton = document.getElementById('start');
  const stopButton = document.getElementById('stop');
  let stream = null;
  let pose = null;
  let running = false;
  let busy = false;

  function elbowAngle(a, b, c) {
    const ba = [a.x - b.x, a.y - b.y];
    const bc = [c.x - b.x, c.y - b.y];
    const denom = Math.hypot(...ba) * Math.hypot(...bc);
    if (!denom) return null;
    const cosine = Math.max(-1, Math.min(1, (ba[0] * bc[0] + ba[1] * bc[1]) / denom));
    return Math.acos(cosine) * 180 / Math.PI;
  }

  function drawResults(results) {
    if (!running) return;
    const w = video.videoWidth || 640;
    const h = video.videoHeight || 480;
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    ctx.save();
    ctx.clearRect(0, 0, w, h);
    if (results.poseLandmarks) {
      ctx.drawImage(results.image, 0, 0, w, h);
      drawConnectors(ctx, results.poseLandmarks, POSE_CONNECTIONS,
                     {color: '#65e6a5', lineWidth: 4});
      drawLandmarks(ctx, results.poseLandmarks,
                    {color: '#ffcf5a', lineWidth: 2, radius: 5});
      const lm = results.poseLandmarks;
      const shoulder = lm[12], elbow = lm[14], wrist = lm[16];
      const visible = shoulder.visibility > 0.45 &&
                      elbow.visibility > 0.45 && wrist.visibility > 0.45;
      const angle = visible ? elbowAngle(shoulder, elbow, wrist) : null;
      if (angle !== null) {
        angleLabel.textContent = angle.toFixed(1) + '°';
        status.textContent = 'Tracking right arm.';
        ctx.fillStyle = '#65e6a5';
        ctx.font = 'bold 28px system-ui, sans-serif';
        ctx.fillText(angle.toFixed(1) + '°', 18, 38);
      } else {
        angleLabel.textContent = '--°';
        status.textContent = 'Keep your right shoulder, elbow, and wrist visible.';
      }
    } else {
      angleLabel.textContent = '--°';
      status.textContent = 'No pose detected. Move into the camera view.';
    }
    ctx.restore();
  }

  async function processFrame() {
    if (!running || busy) return;
    if (video.readyState >= 2 && pose) {
      busy = true;
      try { await pose.send({image: video}); }
      catch (err) { status.textContent = 'Tracking error: ' + err.message; }
      busy = false;
    }
    if (running) requestAnimationFrame(processFrame);
  }

  startButton.addEventListener('click', async () => {
    startButton.disabled = true;
    status.textContent = 'Requesting camera access…';
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: {facingMode: 'user'}, audio: false
      });
      video.srcObject = stream;
      await video.play();
      pose = new Pose({locateFile: file =>
        'https://cdn.jsdelivr.net/npm/@mediapipe/pose/' + file});
      pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });
      pose.onResults(drawResults);
      running = true;
      stopButton.disabled = false;
      status.textContent = 'Camera on. Loading pose tracker…';
      requestAnimationFrame(processFrame);
    } catch (err) {
      if (stream) stream.getTracks().forEach(track => track.stop());
      stream = null;
      startButton.disabled = false;
      status.textContent = 'Could not start camera: ' + err.message +
        '. Check browser camera permission and use the HTTPS Replit preview.';
    }
  });

  stopButton.addEventListener('click', async () => {
    running = false;
    if (stream) stream.getTracks().forEach(track => track.stop());
    stream = null;
    video.srcObject = null;
    if (pose) { await pose.close(); pose = null; }
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    angleLabel.textContent = '--°';
    status.textContent = 'Camera is off.';
    startButton.disabled = false;
    stopButton.disabled = true;
  });
})();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    port = int(os.environ.get("PORT") or os.environ.get("REPLIT_PORT") or "3000")
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Elbow Angle Tracker running on port {port}")
    server.serve_forever()
