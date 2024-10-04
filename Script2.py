import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
from google.cloud import storage
import pytz  # Import pytz for timezone handling
from vertexai.generative_models import GenerativeModel, Part, SafetySetting
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import tempfile  # Import tempfile module
import vertexai

st.set_page_config(
    page_title="Welcome",
    page_icon="🏡¡",
    layout="centered",
    initial_sidebar_state="expanded"
)

def show_svg(path):
    with open(path, 'r', encoding='utf-8') as file:
        svg = file.read()
        st.markdown(svg, unsafe_allow_html=True)

path_to_svg = 'Infosys_logo.svg'
show_svg(path_to_svg)

# Google Cloud Storage settings
bucket_name = "bucket_name"
analysis_folder = "folder_name"
key_file_path = "proj_1.json"

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_file_path

# Define the timezone for Berlin (UTC+2)
berlin_timezone = pytz.timezone('Europe/Berlin')

# Initialize DataFrame to store video information and analysis results
video_log = pd.DataFrame(columns=["Video Title", "Upload Time", "Created Time", "Analysis"])

# Initialize Google Cloud Storage client and retrieve file metadata
storage_client = storage.Client.from_service_account_json(key_file_path)

# Access a specific bucket and list contents only in the 'robot' folder
bucket = storage_client.bucket(bucket_name)
prefix = "robot/"  # Specify the folder to list files from
blobs = list(bucket.list_blobs(prefix=prefix))

# Sort blobs by creation time (oldest first)
blobs.sort(key=lambda x: x.time_created)

# List to store file information
file_info_list = []

# Iterate over each blob to get the file information
for blob in blobs:
    file_name = blob.name
    if blob.time_created:
        # Convert to the specified timezone (UTC+2)
        created_time_utc = blob.time_created.replace(tzinfo=pytz.UTC)
        created_time_berlin = created_time_utc.astimezone(berlin_timezone)

        # Format the created time to a more friendly format
        created_time = created_time_berlin.strftime("%Y-%m-%d %H:%M:%S")
        created_date = created_time_berlin.date().isoformat()
        time_ = created_time_berlin.strftime("%H:%M:%S")  # Extract only the time part
    else:
        created_time = "Not available"
        created_date = "Not available"
        time_ = "Not available"

    # Append the file information to the list
    file_info_list.append({
        "file_name": file_name,
        "created_date": created_date,
        "created_time": created_time,
        "time_": time_  # Add the new time_only field
    })

# Create a DataFrame from the list of file information
df = pd.DataFrame(file_info_list)

# Function to upload the file to Google Cloud Storage
def upload_to_gcs(local_file, bucket_name, destination_blob_name):
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(local_file)
        upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.write(f"File uploaded successfully to {destination_blob_name} at {upload_time}")
        return upload_time
    except Exception as e:
        st.write(f"Error uploading file to GCS: {str(e)}")
        return None

# Function to analyze a video
def analyze_video(video_filename, prompt_text):
    st.write(f"Analyzing {video_filename}...")

    vertexai.init(project="project name, location="us-central1")
    
    model = GenerativeModel("gemini-1.5-flash-001")

    # Use the provided prompt_text from the user input
    video1 = Part.from_uri(mime_type="video/mp4", uri=f"gs://{bucket_name}/{analysis_folder}/{video_filename}")

    safety_settings = [
        SafetySetting(category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH, 
                      threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
        SafetySetting(category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, 
                      threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
        SafetySetting(category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, 
                      threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
        SafetySetting(category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT, 
                      threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
    ]

    responses = model.generate_content([prompt_text, video1], safety_settings=safety_settings, stream=True)
    
    result_text = ""
    for response in responses:
        result_text += response.text

    # Limit to max 250 words
    result_text = ' '.join(result_text.split()[:250])
    return result_text

# Function to convert DataFrame to PDF and upload
def save_analysis_to_pdf(video_log):
    try:
        pdf_file = "video_analysis2.pdf"
        pdf_path = os.path.join(tempfile.gettempdir(), pdf_file)  # Use tempfile to generate a temp file path

        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Use a smaller font size for the table
        small_style = styles['Normal']
        small_style.fontSize = 8  # Reduce font size

        # Convert DataFrame to list of lists for table
        data = [video_log.columns.tolist()]  # Header row
        for index, row in video_log.iterrows():
            # Create paragraphs for each cell to handle text wrapping and size
            row_data = [
                Paragraph(str(row["Video Title"]), small_style),
                Paragraph(str(row["Upload Time"]), small_style),
                Paragraph(str(row["Created Time"]), small_style),
                Paragraph(str(row["Analysis"]), small_style),
            ]
            data.append(row_data)

        # Set column widths
        table = Table(data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 5.1*inch])  # Adjust colWidths for Analysis column
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Align text to the top
        ]))

        elements.append(table)
        doc.build(elements)

        st.write("PDF file generated successfully.")

        # Upload to GCS
        upload_result = upload_to_gcs(pdf_path, bucket_name, f"{analysis_folder}/{pdf_file}")
        if upload_result:
            st.write("PDF file uploaded successfully.")
        else:
            st.write("PDF file upload failed.")

        # Clean up temporary file
        os.unlink(pdf_path)
    except Exception as e:
        st.write(f"Error saving analysis to PDF: {str(e)}")

# Streamlit App
st.title("Video Analysis and Report Generation 🗒️")

# Editable prompt for the user
default_prompt ="""You are analyzing the video {video_filename}. Provide a detailed summary of the video content in max 250 words, provide a lot of details.  is a person taking anything in the video (include the answer only if someone takes or is carrying away something)? do not provide any sound info.
Provide the events (only clear facts) in the sequence (you can provide an info what happened in the video and what a person was doing). Is any person in the video taking taking anything? (mention only if that happens). If there is one person use a singular form.
Count only people who are directly in front of the camera (ignore reflection in the glass).
 If there no people, say there is no people instead of 0 or zero."""
prompt_text = st.text_area("Enter your prompt:", default_prompt)

# Function to check for videos and analyze them
def analyze_videos():
    storage_client = storage.Client.from_service_account_json(key_file_path)  # Initialize storage client
    bucket = storage_client.bucket(bucket_name)
    prefix = "robot/"  # Define the folder prefix

    # List contents of the 'robot' folder
    blobs = list(bucket.list_blobs(prefix=prefix))

    # Sort blobs by creation time (oldest first)
    blobs.sort(key=lambda x: x.time_created)

    for blob in blobs:
        try:
            video_filename = blob.name.replace(prefix, "")

            # Check if the blob name matches the video file naming pattern
            if not video_filename.startswith("video_") or not video_filename.endswith(".mp4"):
                continue

            # Retrieve created time from DataFrame
            created_time_row = df[df["file_name"] == blob.name]
            if not created_time_row.empty:
                created_time_str = created_time_row.iloc[0]["created_time"]
            else:
                created_time_str = "Not available"

            # Analyze the video with the user-provided or default prompt
            upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            analysis_result = analyze_video(video_filename, prompt_text)
            video_log_entry = {
                "Video Title": video_filename,
                "Upload Time": upload_time,
                "Created Time": created_time_str,
                "Analysis": analysis_result
            }
            video_log.loc[len(video_log)] = video_log_entry
            st.write(f"Analysis for {video_filename}: {analysis_result}")

            # Wait for 60 seconds before processing the next video
            time.sleep(10)

        except Exception as e:
            st.write(f"Error analyzing {video_filename}: {str(e)}")
            continue

# Run analysis if the button is clicked
if st.button("Start Analysis"):
    analyze_videos()

    # Save the DataFrame as a PDF file
    save_analysis_to_pdf(video_log)
