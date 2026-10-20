# Elbow Angle Estimator

Estimate your left and right elbow angles in real time using your webcam. 


> **Live demo:** https://elbowangles.netlify.app/

## Preview

Start the camera to see the live feed with arm-only tracking and live angle readings.

## Features

- **Left and right elbow angle estimates** displayed in degrees.
- **Smoothed readings** to reduce rapid frame-to-frame fluctuations.
- **Runs in the browser:** the page does not upload the camera feed to a project backend.

## Try it

1. Open the live demo using the link above.
2. Allow camera access when your browser asks.
3. Stand far enough back for your shoulders, elbows, and wrists to be visible.
4. Turn slightly sideways to the camera for a clearer 2D angle estimate.

A nearly straight arm should read close to **180°**, and a bend near a right angle should read close to **90°**.

## Run locally

You need Python 3 installed, plus an internet connection to load the MediaPipe model and browser libraries.

1. Clone this repository:
   ```bash
   git clone https://github.com/Madheysh/Elbow-angles.git
   cd Elbow-angles
   ```
2. Start a local web server:
   ```bash
   python3 -m http.server 8000
   ```
3. Open [http://localhost:8000](http://localhost:8000) in a modern browser and allow camera access.

Opening the HTML file directly may prevent camera access or module loading. Use localhost or an HTTPS deployment instead.

## How it works

The app uses MediaPipe's browser-based Pose Landmarker to estimate body landmarks from each camera frame. It calculates the angle at each elbow from the shoulder, elbow, and wrist coordinates in the **2D camera image**. A small smoothing step makes the displayed values less jittery.

Because this is a 2D estimate, camera perspective, body rotation, poor lighting, and hidden landmarks can affect accuracy.
## Tech stack

- HTML, CSS, and JavaScript
- [MediaPipe Tasks Vision](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/web_js)
- Browser webcam API

## Acknowledgements

Thanks to the MediaPipe team for the browser-based pose estimation tools.
