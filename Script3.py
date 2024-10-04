import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain_google_vertexai import ChatVertexAI, VertexAI, VertexAIEmbeddings
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
import os
from google.cloud import storage
import vertexai
from vertexai.generative_models import GenerativeModel
from langchain_core.messages import HumanMessage, SystemMessage


st.set_page_config(
    page_title="Welcome",
    page_icon="🏡¡",
    layout="centered",
   # layout="centered",
    initial_sidebar_state="expanded"
)

def show_svg(path):
    with open(path, 'r', encoding='utf-8') as file:
        svg = file.read()
        st.markdown(svg, unsafe_allow_html=True)
path_to_svg = 'Infosys_logo.svg'


show_svg(path_to_svg)





# 
# st.set_page_config(page_title="Chat PDF", layout="centered")

# Initialize Google Cloud and Vertex AI settings
key_file_path = "proj_1.json"  # Path to service account key file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_file_path  # Set environment variable for GCP credentials

vertexai.init(project="project_name", location="us-central1")
model = GenerativeModel("gemini-1.5-flash-001")

# Configuration for GCS and file paths
bucket_name = "bucket_name"
analysis_folder = "folder_name"  # Folder in the GCS bucket for PDFs
pdf_filename = "video_analysis_demo.pdf"  # Name of the PDF file in GCS
source_blob_name = f"{analysis_folder}/{pdf_filename}"  # Full path to the file in GCS
destination_file_name = "/tmp/latest-pdf-file.pdf"  # Local path for downloading the file

def download_pdf_from_gcs(bucket_name, source_blob_name, destination_file_name):
    """Download the PDF file from Google Cloud Storage, ensuring it's the latest version."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)

    if os.path.exists(destination_file_name):
        os.remove(destination_file_name)  # Remove the old PDF if it exists
    
    blob.download_to_filename(destination_file_name)
    st.write(f"Downloaded the latest PDF from GCS: {source_blob_name}")
    return destination_file_name

def list_video_files(bucket_name, analysis_folder):
    """List video files in the specified Google Cloud Storage bucket and folder."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=analysis_folder)

    video_files = [blob.name for blob in blobs if blob.name.endswith(('.mp4', '.avi', '.mkv'))]
    return video_files

def download_video_from_gcs(bucket_name, video_blob_name):
    """Download a video file from Google Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(video_blob_name)
    local_video_path = f"/tmp/{os.path.basename(video_blob_name)}"
    blob.download_to_filename(local_video_path)
    return local_video_path

def get_pdf_text(pdf_path):
    """Extract text from a PDF file."""
    text = ""
    pdf_reader = PdfReader(pdf_path)
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def get_text_chunks(text):
    """Split text into chunks for processing."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks

def extract_created_time(pdf_text):
    """Extract the created time from the PDF text."""
    # Assuming the created time is in the format "Created Time: <time_value>" in the PDF
    lines = pdf_text.split("\n")
    for line in lines:
        if "Created Time:" in line:
            return line.replace("Created Time:", "").strip()
    return "No created time found."

def get_vector_store(text_chunks):
    """Create and save a vector store using FAISS."""
    embeddings = VertexAIEmbeddings("text-embedding-004")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)

    vector_store.save_local("faiss_index")
    st.write("Vector store created and saved.")

def get_conversational_chain(created_time):
    """Set up the conversational chain for question answering."""
    # Define the system's understanding of suspicious behavior and time handling
    prompt_template = f"""
    You are analyzing video footage for suspicious behavior. The following actions should be flagged as suspicious:
    1. Anyone entering a cage/metal gate that holds electrical systems. This area is restricted, and no one should be inside unless authorized.
    2. Handling, lifting, or carrying a fire extinguisher unless there is a clear emergency or need. In non-emergency contexts, this is unusual.
    

    Always base your answers on the context provided in the PDF report and video analysis results.
    
    If the behavior mentioned relates to entering the restricted cage or handling a fire extinguisher, consider it suspicious and flag it.
    If someone asks about the time something happened, provide the created time: {created_time}.
    
    Otherwise, answer the question as detailed as possible based on the provided context. If the answer is not in the provided context, say,
    "The answer is not available in the context."
    
    Context:\n {{context}}\n
    Question: \n{{question}}\n

    Answer:
    """

    model = ChatVertexAI(model="gemini-1.5-pro", temperature=0.3)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)

    return chain

def user_input(user_question, created_time):
    """Process user input and return an answer."""
    embeddings = VertexAIEmbeddings("text-embedding-004")
    
    new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    docs = new_db.similarity_search(user_question)

    chain = get_conversational_chain(created_time)

    response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)

    st.write("Reply: ", response["output_text"])

def main():
    st.header("Ask questions about the recordings 🙋🏻‍♀️")

    # Always download the latest PDF from GCS
    pdf_path = download_pdf_from_gcs(bucket_name, source_blob_name, destination_file_name)

    # Extract text and generate chunks
    pdf_text = get_pdf_text(pdf_path)
    created_time = extract_created_time(pdf_text)  # Extract the created time
    text_chunks = get_text_chunks(pdf_text)

    # Generate and save the vector store (FAISS index) from the latest PDF
    get_vector_store(text_chunks)

    # Ask questions based on the latest PDF
    user_question = st.text_input("Ask a Question from the PDF Files")

    if user_question:
        user_input(user_question, created_time)

    # List available video files and create a dropdown
    video_files = list_video_files(bucket_name, analysis_folder)

    selected_video = st.selectbox("Select a video file to analyze", video_files)

    if selected_video:
        local_video_path = download_video_from_gcs(bucket_name, selected_video)
        st.video(local_video_path)

    # Serve the PDF file as a downloadable link
    with open(pdf_path, "rb") as pdf_file:
        st.download_button(
            label="Download PDF Report",
            data=pdf_file,
            file_name=pdf_filename,
            mime="application/pdf"
        )

if __name__ == "__main__":
    main()
