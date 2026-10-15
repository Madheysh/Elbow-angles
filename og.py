import cv2
import mediapipe as mp
import numpy as np
import serial
import time

mp_pose = mp.solutions.pose

print("Running pose tracker!")

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("ERROR: Camera didn't open. Check camera permission for Terminal in "
          "System Settings > Privacy & Security > Camera, or try index 1.")
    exit()

points_to_track = {
    "LEFT_SHOULDER": (0, 255, 255),
    "RIGHT_SHOULDER": (0, 255, 255),
    "LEFT_ELBOW": (255, 0, 0),
    "RIGHT_ELBOW": (255, 0, 0),
    "LEFT_WRIST": (255, 0, 255),
    "RIGHT_WRIST": (255, 0, 255),
}


def angle_between(a, b, c):
    v1 = a - b
    v2 = c - b
    v1_u = v1 / np.linalg.norm(v1)
    v2_u = v2 / np.linalg.norm(v2)
    dot_prod = np.dot(v1_u, v2_u)
    return np.degrees(np.arccos(np.clip(dot_prod, -1.0, 1.0)))


with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Frame not read — camera disconnected or permission blocked.")
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        if results.pose_landmarks:
            h, w, _ = frame.shape
            landmarks = results.pose_landmarks.landmark

            def pt(name):
                lm = landmarks[getattr(mp_pose.PoseLandmark, name)]
                return np.array([lm.x * w, lm.y * h])

            r_shoulder = pt("RIGHT_SHOULDER")
            r_elbow = pt("RIGHT_ELBOW")
            r_wrist = pt("RIGHT_WRIST")

            r_angle = angle_between(r_shoulder, r_elbow, r_wrist)

            # --- serial send moved here: r_angle now exists, runs every frame ---
       
            # ----------------------------------------------------------------

            cv2.putText(frame, f"{r_angle:.1f} deg", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            for name, color in points_to_track.items():
                p = pt(name)
                cv2.circle(frame, (int(p[0]), int(p[1])), 8, color, -1)
        else:
            print("No landmarks detected this frame.")

        cv2.imshow('Multi Landmark Tracking', frame)
        if cv2.waitKey(5) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
