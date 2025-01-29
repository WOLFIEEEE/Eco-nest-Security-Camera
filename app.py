import cv2
import time
import os
import logging
import threading
from datetime import datetime
from flask import Flask, Response, request, send_from_directory, jsonify, g, render_template
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from queue import Queue
import numpy as np

###############################################################################
# Configuration
###############################################################################
VIDEO_STORAGE_DIR = 'videos'            # Directory to store video files
ANOMALY_STORAGE_DIR = 'anomalies'       # Directory to store anomaly photos
VIDEO_DURATION = 30 * 60                # Duration of each video chunk (30 minutes)
MAX_VIDEO_DURATION = 12 * 60 * 60       # Keep recordings for 12 hours
MAX_ANOMY_IMAGES = 2000                  # Keep up to 2000 anomaly images
FRAME_WIDTH = 640                        # Width of the video frame
FRAME_HEIGHT = 480                       # Height of the video frame
FPS = 10                                 # Reduced Frames per second for recording and streaming
# User credentials
USERS = {
    'sneh': generate_password_hash('bhat'),
    'akash': generate_password_hash('singh'),
    'khushwant': generate_password_hash('parihar')
}
CAMERA_INDEX = 0                        # Usually 0 for USB camera
VAR_THRESHOLD = 50                      # Anomaly detection sensitivity
CONTOUR_AREA_THRESHOLD = 20000          # Min area to consider an anomaly
ANOMALY_COOLDOWN = 5.0                  # Wait 5 seconds after capturing an anomaly
LOG_LEVEL = logging.INFO                # Logging level (DEBUG, INFO, WARNING, etc.)

###############################################################################
# Logging Setup
###############################################################################
logging.basicConfig(
    level=LOG_LEVEL,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

###############################################################################
# Flask App & Authentication
###############################################################################
app = Flask(__name__)
auth = HTTPBasicAuth()

# Hard-coded user dictionary
users = USERS

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        g.user = username  # Store the username in Flask's g context
        return username
    return None

###############################################################################
# Shared Camera Class with Frame Queue
###############################################################################
class SharedCamera:
    """
    A shared camera class that continuously captures frames in a dedicated thread.
    Uses a queue to distribute frames to different consumers without blocking.
    """
    def __init__(self, camera_index=0, queue_size=10):
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            logging.critical(f"Cannot open camera at index {camera_index}. Exiting.")
            exit(1)

        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, FPS)

        self.frame_queue = Queue(maxsize=queue_size)
        self.running = True
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

        logging.info("SharedCamera initialized and capture thread started.")

    def update(self):
        """
        Continuously read frames from the camera and put them into the queue.
        """
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                logging.warning("Failed to read frame from camera.")
                time.sleep(0.1)
                continue
            if not self.frame_queue.full():
                self.frame_queue.put(frame)
            else:
                # If the queue is full, discard the oldest frame
                self.frame_queue.get()
                self.frame_queue.put(frame)
        self.cap.release()
        logging.info("Camera capture thread stopped.")

    def get_frame(self):
        """
        Get the latest frame from the queue without blocking.
        """
        if not self.frame_queue.empty():
            return self.frame_queue.get()
        return None

    def stop(self):
        """
        Signal the capture thread to stop and wait for it to finish.
        """
        self.running = False
        self.thread.join()
        logging.info("SharedCamera stopped.")

###############################################################################
# Global Camera Instance
###############################################################################
camera = SharedCamera(camera_index=CAMERA_INDEX)

###############################################################################
# Helper Functions
###############################################################################
def enhance_frame(frame):
    """
    Enhance the frame for better visibility in low-light conditions.
    Applies histogram equalization and gamma correction.
    """
    # Convert to YUV color space
    yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
    
    # Apply Histogram Equalization to the Y channel
    yuv[:, :, 0] = cv2.equalizeHist(yuv[:, :, 0])
    
    # Convert back to BGR
    enhanced_frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
    
    # Apply Gamma Correction
    gamma = 1.5  # Adjust gamma value as needed
    look_up_table = np.array([((i / 255.0) ** gamma) * 255
                             for i in range(256)], dtype="uint8")
    enhanced_frame = cv2.LUT(enhanced_frame, look_up_table)
    
    return enhanced_frame

def manage_storage():
    """
    1) Deletes video files older than MAX_VIDEO_DURATION (12 hours).
    2) Ensures we don't store more than MAX_ANOMY_IMAGES (2000).
    3) Also ensures anomaly photos older than MAX_VIDEO_DURATION get removed.
    """
    now = time.time()
    cutoff = now - MAX_VIDEO_DURATION

    # Ensure directories exist
    os.makedirs(VIDEO_STORAGE_DIR, exist_ok=True)
    os.makedirs(ANOMALY_STORAGE_DIR, exist_ok=True)

    # Manage video files by time
    for filename in os.listdir(VIDEO_STORAGE_DIR):
        if filename.startswith("video_") and filename.endswith(".mp4"):
            filepath = os.path.join(VIDEO_STORAGE_DIR, filename)
            timestamp_str = filename.replace("video_", "").replace(".mp4", "")
            try:
                file_time = time.mktime(datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").timetuple())
                if file_time < cutoff:
                    os.remove(filepath)
                    logging.info(f"Deleted old video file: {filepath}")
            except Exception as e:
                logging.error(f"Error parsing video filename '{filename}': {e}")

    # Manage anomaly files by time and count
    anomaly_files = []
    for filename in os.listdir(ANOMALY_STORAGE_DIR):
        if filename.startswith("anomaly_") and filename.endswith(".jpg"):
            filepath = os.path.join(ANOMALY_STORAGE_DIR, filename)
            anomaly_files.append(filepath)

    # Sort anomaly files by creation time (based on filename)
    def extract_time(fpath):
        base = os.path.basename(fpath)
        time_str = base.replace("anomaly_", "").replace(".jpg", "")
        try:
            return datetime.strptime(time_str, "%Y%m%d_%H%M%S")
        except:
            return datetime.now()  # fallback if parse fails

    anomaly_files.sort(key=lambda x: extract_time(x), reverse=True)  # Latest first

    # Delete anomalies older than cutoff
    for filepath in anomaly_files:
        base = os.path.basename(filepath)
        timestamp_str = base.replace("anomaly_", "").replace(".jpg", "")
        try:
            file_time = time.mktime(datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").timetuple())
            if file_time < cutoff:
                os.remove(filepath)
                logging.info(f"Deleted old anomaly file: {filepath}")
        except Exception as e:
            logging.error(f"Error parsing anomaly filename '{base}': {e}")

    # If more than MAX_ANOMY_IMAGES remain, remove oldest
    anomaly_files = [os.path.join(ANOMALY_STORAGE_DIR, f) for f in os.listdir(ANOMALY_STORAGE_DIR)
                     if f.startswith("anomaly_") and f.endswith(".jpg")]
    if len(anomaly_files) > MAX_ANOMY_IMAGES:
        # Sort again (latest first)
        anomaly_files.sort(key=lambda x: extract_time(x), reverse=True)
        excess = len(anomaly_files) - MAX_ANOMY_IMAGES
        for i in range(excess):
            os.remove(anomaly_files[-1])  # Remove the oldest
            logging.info(f"Deleted anomaly file to maintain max count: {anomaly_files[-1]}")

###############################################################################
# Flask Routes
###############################################################################
@app.route('/')
def index():
    """
    Default route: render the home page with instructions and link to /camera.
    """
    username = getattr(g, 'user', 'Guest')
    logging.info(f"Client '{username}' visited root (/). Showing home page.")
    return render_template('index.html')

@app.errorhandler(404)
def page_not_found(e):
    """
    Custom handler for unknown routes.
    """
    username = getattr(g, 'user', 'Guest')
    logging.warning(f"Client '{username}' visited an unknown route.")
    return render_template('404.html'), 404

@app.route('/camera')
@auth.login_required
def camera_page():
    """
    HTML page containing the live feed and recent anomaly photos.
    """
    username = g.get('user', 'User')
    logging.info(f"Client '{username}' requested /camera page.")
    return render_template('camera.html', username=username)

@app.route('/video_feed')
@auth.login_required
def video_feed():
    """
    Route to stream the video feed as MJPEG.
    """
    username = g.get('user', 'User')
    logging.info(f"Client '{username}' requested /video_feed. Starting MJPEG stream.")
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/anomalies/<filename>')
@auth.login_required
def get_anomaly_image(filename):
    """
    Route to serve anomaly images.
    """
    username = g.get('user', 'User')
    logging.info(f"Client '{username}' requested anomaly image: {filename}")
    return send_from_directory(ANOMALY_STORAGE_DIR, filename)

@app.route('/get_anomalies')
@auth.login_required
def get_anomalies():
    """
    Route to return a JSON list of anomaly image URLs.
    Supports pagination with 'page' and 'per_page' query parameters.
    """
    username = g.get('user', 'User')
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=20, type=int)

    # Get list of anomaly images sorted by newest first
    anomaly_files = [f for f in os.listdir(ANOMALY_STORAGE_DIR) if f.startswith("anomaly_") and f.endswith(".jpg")]
    anomaly_files.sort(reverse=True)  # Latest first

    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated_files = anomaly_files[start:end]

    # Generate URLs
    images = [{'url': f'/anomalies/{filename}'} for filename in paginated_files]

    logging.info(f"Client '{username}' fetched anomalies: page {page}, per_page {per_page}")
    return jsonify({'images': images})

###############################################################################
# Frame Generator
###############################################################################
def generate_frames():
    """
    Generator function that yields JPEG frames from the shared camera.
    """
    while True:
        frame = camera.get_frame()
        if frame is None:
            logging.debug("No frame available yet, waiting...")
            time.sleep(0.05)
            continue

        # **Enhance the frame for low-light conditions**
        enhanced = enhance_frame(frame)

        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', enhanced)
        if not ret:
            logging.warning("Failed to encode frame to JPEG.")
            continue

        # Yield the frame in byte format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

###############################################################################
# Video Recording Thread
###############################################################################
def record_video():
    """
    Continuously record the camera feed in chunks (default 30 mins), saving MP4 files
    and managing storage to keep only 12 hours of content.
    """
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = None
    end_time = time.time() + VIDEO_DURATION

    logging.info("Video recording thread started.")

    while True:
        frame = camera.get_frame()
        if frame is None:
            logging.debug("No frame available for recording.")
            time.sleep(0.05)
            continue

        if video_writer is None:
            # Start a new video file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_filename = os.path.join(VIDEO_STORAGE_DIR, f"video_{timestamp}.mp4")
            logging.info(f"Starting new recording file: {video_filename}")
            video_writer = cv2.VideoWriter(video_filename, fourcc, FPS, (FRAME_WIDTH, FRAME_HEIGHT))
            end_time = time.time() + VIDEO_DURATION

        video_writer.write(frame)

        # Time to start a new chunk?
        if time.time() >= end_time:
            logging.info("Reached end of video chunk duration. Closing file and starting new one.")
            video_writer.release()
            video_writer = None

        # Manage old files periodically to reduce overhead
        if int(time.time()) % 300 == 0:  # Every 5 minutes
            manage_storage()

        time.sleep(1 / FPS)

###############################################################################
# Anomaly Detection Thread
###############################################################################
def detect_anomalies():
    """
    Uses background subtraction to detect large motion anomalies in the shared camera feed.
    Saves JPEG photos on detection but then waits 5 seconds (ANOMALY_COOLDOWN) before taking
    another anomaly photo to prevent spam.
    """
    logging.info("Anomaly detection thread started.")

    backSub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=VAR_THRESHOLD, detectShadows=True)
    last_capture_time = 0  # track last anomaly capture

    while True:
        frame = camera.get_frame()
        if frame is None:
            logging.debug("No frame available for anomaly detection.")
            time.sleep(0.05)
            continue

        # Apply background subtraction
        fgMask = backSub.apply(frame)

        # Threshold the mask to remove shadows (gray areas)
        _, thresh = cv2.threshold(fgMask, 250, 255, cv2.THRESH_BINARY)

        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        anomaly_detected = False
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > CONTOUR_AREA_THRESHOLD:
                anomaly_detected = True
                break

        # If an anomaly is detected, check cooldown
        if anomaly_detected:
            now = time.time()
            if now - last_capture_time >= ANOMALY_COOLDOWN:
                # Save anomaly image
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                anomaly_filename = os.path.join(ANOMALY_STORAGE_DIR, f"anomaly_{timestamp}.jpg")
                cv2.imwrite(anomaly_filename, frame)
                logging.info(f"Anomaly detected! Photo saved: {anomaly_filename}")
                last_capture_time = now
            else:
                logging.debug("Anomaly detected but still in cooldown.")

        # Manage storage periodically to reduce overhead
        if int(time.time()) % 60 == 0:  # Every minute
            manage_storage()

        time.sleep(0.1)

###############################################################################
# Main Entry Point
###############################################################################
if __name__ == '__main__':
    # Make sure the storage directories exist
    os.makedirs(VIDEO_STORAGE_DIR, exist_ok=True)
    os.makedirs(ANOMALY_STORAGE_DIR, exist_ok=True)

    # Start recording in a separate thread
    recording_thread = threading.Thread(target=record_video, daemon=True)
    recording_thread.start()
    logging.info("Recording thread initialized.")

    # Start anomaly detection in a separate thread
    anomaly_thread = threading.Thread(target=detect_anomalies, daemon=True)
    anomaly_thread.start()
    logging.info("Anomaly detection thread initialized.")

    # Run Flask app to serve the default page, camera page, and MJPEG feed
    logging.info("Starting Flask server on port 5000...")
    app.run(host='0.0.0.0', port=5000, threaded=True)

    # When the Flask server exits, we can stop the camera if desired
    camera.stop()
    logging.info("EcoNest Security Camera script shutting down.")