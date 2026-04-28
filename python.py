import cv2
import mediapipe as mp
import serial
import time

# --- CONFIGURATION ---
COM_PORT = 'COM22'      # Update to your STM32's COM port
BAUD_RATE = 115200

# Initialize Serial Connection
try:
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.1)
    print(f"Successfully connected to STM32 on {COM_PORT}")
except serial.SerialException as e:
    print(f"Error opening serial port: {e}")
    exit()

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

# --- YOUR MATH FUNCTIONS ---
def calculate_wrist_speed(wrist_landmark):
    """
    Map the wrist's physical position or angle to a 0-100 speed.
    For this example, we map the Y-axis (up/down) position to speed.
    """
    # MediaPipe Y coordinates go from 0.0 (top of screen) to 1.0 (bottom)
    # Let's say moving your wrist up increases speed.
    y_pos = wrist_landmark.y 
    speed = int((1.0 - y_pos) * 100)
    
    # Clamp between 0 and 100 just to be safe
    return max(0, min(100, speed))

def calculate_elbow_speed(elbow_landmark):
    """
    Map the elbow's physical position or angle to a 0-100 speed.
    """
    y_pos = elbow_landmark.y
    speed = int((1.0 - y_pos) * 100)
    return max(0, min(100, speed))

# --- MAIN LOOP ---
cap = cv2.VideoCapture(0) # Open webcam

print("Starting tracking... Press 'q' in the video window to quit.")

while cap.isOpened():
    success, image = cap.read()
    if not success:
        break

    # Convert the image color space for MediaPipe
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = pose.process(image_rgb)

    wrist_speed = 0
    elbow_speed = 0

    # If we detect a person...
    if results.pose_landmarks:
        # Draw the skeleton on the image so you can see it
        mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # Get the specific landmarks (Example using the RIGHT arm)
        # Landmark 14 is Right Elbow, 16 is Right Wrist
        landmarks = results.pose_landmarks.landmark
        right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value]
        right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value]

        # Calculate your speeds
        wrist_speed = calculate_wrist_speed(right_wrist)
        elbow_speed = calculate_elbow_speed(right_elbow)

    # --- SEND TO STM32 ---
    # We send this continuously so the motors update in real-time
    command = f"{wrist_speed},{elbow_speed}\n".encode('utf-8')
    ser.write(command)
    
    # Optional: Print to console so you can debug what it's sending
    print(f"Sent -> Wrist (M1): {wrist_speed}% | Elbow (M2): {elbow_speed}%")

    # Show the video feed
    cv2.imshow('Tracking Feed', image)

    # Break loop if 'q' is pressed
    if cv2.waitKey(5) & 0xFF == ord('q'):
        break

# --- CLEANUP ---
print("Closing down...")
ser.write(b'0,0\n') # Safely stop both motors before quitting!
time.sleep(0.1)
ser.close()
cap.release()
cv2.destroyAllWindows()
