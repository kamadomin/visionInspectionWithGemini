
# Video recording and uploading to Google Dirve

import streamlit as st
import cv2
import tempfile
import os
import time
from datetime import datetime
import pandas as pd
from google.cloud import storage
import subprocess  # For video conversion using ffmpeg

# Google Cloud Storage settings
bucket_name = "bucket_name"  # Updated bucket name
analysis_folder = "folder_name"  # Subfolder within the bucket for storing videos and CSV
key_file_path = "proj_1.json"  # Path to service account key file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_file_path  # Set environment variable for GCP credentials

# Ensure the result_images directory exists
images_dir = 'result_images'
os.makedirs(images_dir, exist_ok=True)

frame_width, frame_height = 1280, 720

# RTSP source
source_cam = 'rtsp of the the device'

# Initialize DataFrame to store video information and analysis results
if 'video_log' not in st.session_state:
    st.session_state.video_log = pd.DataFrame(columns=["Video Title", "Upload Time", "Recording Time"])

# Function to upload the file to Google Cloud Storage
def upload_to_gcs(local_file, bucket_name, destination_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_file)
    blob.content_type = 'video/mp4'  # Explicitly set MIME type to video/mp4
    blob.patch()  # Update the blob metadata
    upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return upload_time

# Function to initialize the camera
def init_camera(source_camera):
    # Setup camera capture
    if 'cap' not in st.session_state or not st.session_state.cap.isOpened():
        st.session_state.cap = cv2.VideoCapture(source_camera)
        if not st.session_state.cap.isOpened():
            st.error('Failed to open camera')
        
        st.session_state.cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
        st.session_state.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

# Function to release the camera
def release_camera():
    if 'cap' in st.session_state:
        st.session_state.cap.release()

# Function to convert the video to MP4 using ffmpeg
def convert_to_mp4(input_file, output_file):
    try:
        subprocess.run(['ffmpeg', '-i', input_file, '-vcodec', 'libx264', output_file], check=True)
        return output_file
    except subprocess.CalledProcessError as e:
        st.error(f"Error converting video to MP4: {e}")
        return None

# Function to record and upload a single video
def record_and_upload_video(video_number):
    raw_video_filename = f"video_{video_number}.avi"
    mp4_video_filename = f"video_{video_number}.mp4"
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.avi')

    # Update the placeholder with the currently recording video filename
    current_video_placeholder.text(f"Currently recording: {mp4_video_filename}")

    init_camera(source_cam)  # Initialize the RTSP camera

    # Using XVID codec for AVI format
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(temp_file.name, fourcc, 20.0, (int(st.session_state.cap.get(3)), int(st.session_state.cap.get(4))))

    start_time = time.time()
    recording_start_time = datetime.now()
    rounded_recording_time = recording_start_time.strftime("%H:%M")  # Round to nearest minute and show only time
    st.session_state.recording_time = rounded_recording_time  # Store the rounded recording time

    stframe = st.empty()  # Placeholder for the video stream
    while time.time() - start_time < 30:  # Record for 30 seconds
        ret, frame = st.session_state.cap.read()
        if not ret:
            st.write("Failed to capture image. Exiting...")
            break
        out.write(frame)
        stframe.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), channels="RGB")

    out.release()  # Ensure the video is finalized and written correctly
    release_camera()  # Release the camera
    stframe.empty()  # Clear the current frame after recording is done

    # Convert the recorded AVI file to MP4
    converted_video_path = os.path.join(tempfile.gettempdir(), mp4_video_filename)
    converted_file = convert_to_mp4(temp_file.name, converted_video_path)

    if converted_file:
        upload_time = upload_to_gcs(converted_file, bucket_name, f"{analysis_folder}/{mp4_video_filename}")
        st.session_state.last_video_file = mp4_video_filename
        st.session_state.upload_time = upload_time

        # Update DataFrame with new video information before analysis
        new_entry = pd.DataFrame({
            "Video Title": [mp4_video_filename], 
            "Upload Time": [upload_time], 
            "Recording Time": [rounded_recording_time],  # Use rounded time
        })
        st.session_state.video_log = pd.concat([st.session_state.video_log, new_entry], ignore_index=True)

        os.unlink(temp_file.name)  # Remove the raw AVI file
        os.unlink(converted_file)  # Remove the converted MP4 file
    else:
        st.error("Video conversion failed. The video was not uploaded.")

# Main function to manage start/stop functionality
def main():
    st.title("Surveillance and Video Upload")

    # Initialize session state
    if 'recording' not in st.session_state:
        st.session_state.recording = False
    if 'video_count' not in st.session_state:
        st.session_state.video_count = 0
    if 'last_video_file' not in st.session_state:
        st.session_state.last_video_file = None
    if 'upload_time' not in st.session_state:
        st.session_state.upload_time = ""
    if 'recording_time' not in st.session_state:
        st.session_state.recording_time = ""

    # Placeholder to display the currently recording video filename
    global current_video_placeholder
    current_video_placeholder = st.empty()

    # Create a Start/Stop button
    if st.button("Start/Stop"):
        st.session_state.recording = not st.session_state.recording

    # If recording is active, keep recording and uploading videos until stopped
    while st.session_state.recording:
        st.session_state.video_count += 1
        record_and_upload_video(st.session_state.video_count)

        # Check for the Stop button to break the loop
        if not st.session_state.recording:
            break

    # Optionally, you can display the video log below (without the currently recording video)
    if len(st.session_state.video_log) > 0:
        st.write("Video Upload Log")
        st.dataframe(st.session_state.video_log)

if __name__ == "__main__":
    main()
