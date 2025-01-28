import cv2
from flask import Flask, Response
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import threading
import time
import os
from datetime import datetime
import numpy as np

# Configuration
PASSWORD_FILE = 'password.txt'        # File containing the access password
VIDEO_STORAGE_DIR = 'videos'         # Directory to store video files
ANOMALY_STORAGE_DIR = 'anomalies'    # Directory to store anomaly photos
VIDEO_DURATION = 30 * 60             # Duration of each video chunk in seconds (30 minutes)
MAX_VIDEO_DURATION = 12 * 60 * 60    # Maximum storage duration in seconds (12 hours)
FRAME_WIDTH = 640                     # Width of the video frame
FRAME_HEIGHT = 480                    # Height of the video frame
FPS = 20                              # Frames per second for recording
USERNAME = 'user'                     # Username for authentication

app = Flask(__name__)
auth = HTTPBasicAuth()

# Load password from file
def load_password():
    try:
        with open(PASSWORD_FILE, 'r') as f:
            password = f.read().strip()
            return generate_password_hash(password)
    except FileNotFoundError:
        print(f"Password file '{PASSWORD_FILE}' not found.")
        return None

hashed_password = load_password()
if not hashed_password:
    exit("Exiting due to missing password file.")

users = {
    USERNAME: hashed_password  # Username is 'user'; can be modified as needed
}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username
    return None

@app.route('/video_feed')
@auth.login_required
def video_feed():
    """
    Route to stream the video feed.
    """
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_frames():
    """
    Generator function that yields video frames in MJPEG format.
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera for streaming")
        return
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            # Yield frame in byte format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    cap.release()

def record_video():
    """
    Function to record video in 30-minute chunks and manage storage.
    """
    if not os.path.exists(VIDEO_STORAGE_DIR):
        os.makedirs(VIDEO_STORAGE_DIR)
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera for recording")
        return
    
    # Set camera properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FPS)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Using MP4 format
    
    current_time = time.time()
    end_time = current_time + VIDEO_DURATION
    video_writer = None
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame for recording")
            break
        
        if time.time() >= end_time:
            if video_writer:
                video_writer.release()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_filename = os.path.join(VIDEO_STORAGE_DIR, f"video_{timestamp}.mp4")
            video_writer = cv2.VideoWriter(video_filename, fourcc, FPS, (FRAME_WIDTH, FRAME_HEIGHT))
            print(f"Recording new video file: {video_filename}")
            end_time = time.time() + VIDEO_DURATION
        
        if video_writer:
            video_writer.write(frame)
        
        # Manage storage
        manage_storage()
        
        # Sleep to match the FPS
        time.sleep(1 / FPS)
    
    cap.release()
    if video_writer:
        video_writer.release()

def manage_storage():
    """
    Function to delete video and anomaly files older than MAX_VIDEO_DURATION.
    """
    now = time.time()
    cutoff = now - MAX_VIDEO_DURATION

    # Manage video files
    for filename in os.listdir(VIDEO_STORAGE_DIR):
        if filename.startswith("video_") and filename.endswith(".mp4"):
            filepath = os.path.join(VIDEO_STORAGE_DIR, filename)
            # Extract timestamp from filename
            timestamp_str = filename.replace("video_", "").replace(".mp4", "")
            try:
                file_time = time.mktime(datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").timetuple())
                if file_time < cutoff:
                    os.remove(filepath)
                    print(f"Deleted old video file: {filepath}")
            except Exception as e:
                print(f"Error parsing filename {filename}: {e}")

    # Manage anomaly files
    for filename in os.listdir(ANOMALY_STORAGE_DIR):
        if filename.startswith("anomaly_") and filename.endswith(".jpg"):
            filepath = os.path.join(ANOMALY_STORAGE_DIR, filename)
            # Extract timestamp from filename
            timestamp_str = filename.replace("anomaly_", "").replace(".jpg", "")
            try:
                file_time = time.mktime(datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").timetuple())
                if file_time < cutoff:
                    os.remove(filepath)
                    print(f"Deleted old anomaly file: {filepath}")
            except Exception as e:
                print(f"Error parsing filename {filename}: {e}")

def detect_anomalies():
    """
    Function to detect anomalies (e.g., motion detection) and capture photos.
    """
    if not os.path.exists(ANOMALY_STORAGE_DIR):
        os.makedirs(ANOMALY_STORAGE_DIR)
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera for anomaly detection")
        return
    
    # Initialize background subtractor
    backSub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=True)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame for anomaly detection")
            break
        
        # Apply background subtraction
        fgMask = backSub.apply(frame)
        
        # Threshold the mask to eliminate shadows (gray pixels)
        _, thresh = cv2.threshold(fgMask, 250, 255, cv2.THRESH_BINARY)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        anomaly_detected = False
        for contour in contours:
            if cv2.contourArea(contour) > 5000:  # Adjust the area threshold as needed
                anomaly_detected = True
                break
        
        if anomaly_detected:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            anomaly_filename = os.path.join(ANOMALY_STORAGE_DIR, f"anomaly_{timestamp}.jpg")
            cv2.imwrite(anomaly_filename, frame)
            print(f"Anomaly detected! Photo saved: {anomaly_filename}")
        
        # Manage storage
        manage_storage()
        
        # Sleep briefly to reduce CPU usage
        time.sleep(0.1)
    
    cap.release()

if __name__ == '__main__':
    # Start video recording in a separate thread
    recording_thread = threading.Thread(target=record_video, daemon=True)
    recording_thread.start()
    
    # Start anomaly detection in a separate thread
    anomaly_thread = threading.Thread(target=detect_anomalies, daemon=True)
    anomaly_thread.start()
    
    # Start Flask app for streaming
    app.run(host='0.0.0.0', port=5000, threaded=True)