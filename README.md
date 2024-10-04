

Project Description
This project is an end-to-end video analysis and reporting pipeline that leverages Google Cloud Storage, a custom video analysis model (Gemini), 
and an interactive chat interface powered by LangChain. The project consists of three core components:

Script1.py: Video Recording and Uploading: A Streamlit-based application that allows users to record videos directly in the browser and upload them to a specified folder in Google Cloud Storage. 
The user-friendly app enables seamless video storage and management in the cloud for further analysis.

Script2.py: Video Analysis and Report Generation: The second script fetches videos from Google Cloud Storage and analyzes them using a custom video analysis model (Gemini). 
This model processes the video content, identifies key events or behaviors, and generates a detailed report in PDF format. 
Once generated, the PDF report is uploaded to Google Cloud Storage, keeping all relevant data organized and accessible.

Script3.py: Interactive Chat for Event Exploration: The third component is an interactive chat application that allows users to ask questions about the events detected in the analyzed videos. 
Powered by LangChain and Google Vertex AI, the app can provide insightful answers and clarifications about what happened in the video. 
This makes the tool ideal for users seeking deeper insights or detailed explanations of the events captured and analyzed in the videos.
