from flask import Flask, jsonify, request
import json, os, re

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
import io
import os
import base64

# Replace with your service account credentials file path
SERVICE_ACCOUNT_FILE = base64.b64decode(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")).decode()
# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

# Authenticate using service account
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Build the Drive API service
service = build('drive', 'v3', credentials=creds)

def upload_file(file_path, mime_type, file_name=None, folder_id=None):
    """Uploads a file to Google Drive."""

    if file_name is None:
        file_name = os.path.basename(file_path)

    file_metadata = {'name': file_name}
    if folder_id:  # Add folder ID if provided
        file_metadata['parents'] = [folder_id]

    media = MediaFileUpload(file_path, mimetype=mime_type)

    try:
        file = service.files().create(body=file_metadata, media_body=media,
                                    fields='id').execute()
        print(f"File ID: {file.get('id')}")
        return file.get('id')
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None

def download_file(file_id, output_path):
    """Downloads a file from Google Drive."""

    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%.")
        with open(output_path, 'wb') as f:  # Use 'wb' for binary files
            fh.seek(0)
            f.write(fh.getvalue())
        print(f"File downloaded to: {output_path}")
        return True
    except HttpError as error:
        print(f"An error occurred: {error}")
        return False

def send_email(subject, body, to_email):
    sender_email = json.loads(os.getenv("GMAIL_ADDRESS"))
    sender_password = json.loads(os.getenv("GOOGLE_APP_PASSWORD"))
    
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    
    msg.attach(MIMEText(body, "plain"))
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())

def create_enquiry_file(filename, enquiry):
    #enquiry_json = json.dumps(enquiry, indent=4)
    subject = f"New Enquiry"
    send_email(subject, json.dumps(enquiry), "marcellsdave@gmail.com")

app = Flask(__name__)

def dump_json(data, filename):
    with open(filename, 'w') as json_file:
        json.dump(data, json_file, indent=4)

def load_json(filename):
    try:
        if not os.path.exists(filename):
            with open(filename, 'w') as json_file:
                json.dump({}, json_file)

        with open(filename, 'r') as json_file:
            return json.load(json_file)
    except Exception as e:
        print(f"Error loading JSON from {filename}: {e}")
        return {}

waitlist_file_id = ""
enquiries_file_id = ""

def is_valid_email(email):
    return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$", email)

def get_waitlist():
    #if os.environ.get("APP_STATUS") == "dev":
    #    return load_json("waitlist.json")

    download_file(waitlist_file_id, "waitlist.json")
    return load_json("waitlist.json")

def update_waitlist(waitlist):
    dump_json(waitlist, "waitlist.json")
    #if os.environ.get("APP_STATUS") != "dev":
    upload_file("waitlist.json", "text/json")

def create_enquiry_file(filename, enquiry):
    #if os.environ.get("APP_STATUS") == "dev":
    #    os.makedirs("enquiries", exist_ok=True)
    #    dump_json(enquiry, f"enquiries/{filename}")
    #else:
    enquires_folder_id = ""
    upload_file(filename, "text/json", folder_id=enquires_folder_id)

@app.route('/add_to_waitlist', methods=['POST'])
def add_to_waitlist():
    waitlist = get_waitlist()

    if not request.is_json:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    data = request.get_json()
    
    if 'email' not in data or 'business_id' not in data:
        return jsonify({"error": "Missing email or business_id"}), 400
    
    email = data['email']
    #if not is_valid_email(email):
    #    return jsonify({"error": "Invalid email format"}), 400
    
    business_id = data['business_id']
    if business_id not in waitlist:
        waitlist[business_id] = []

    if email not in waitlist[business_id]:
        waitlist[business_id].append(email)
    
    update_waitlist(waitlist)
    
    return jsonify({"message": "OK", "email": email})

@app.route('/remove_from_waitlist', methods=['POST'])
def remove_from_waitlist():
    waitlist = get_waitlist()

    if not request.is_json:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    data = request.get_json()
    if 'email' not in data or 'business_id' not in data:
        return jsonify({"error": "Missing email or business_id"}), 400
    
    email = data['email']
    business_id = data['business_id']

    if business_id not in waitlist or email not in waitlist[business_id]:
        return jsonify({"error": "Email not found in waitlist"}), 404
    
    waitlist[business_id].remove(email)
    update_waitlist(waitlist)
    return jsonify({"message": "Removed", "email": email})

@app.route('/receive_enquiry', methods=['POST'])
def receive_enquiry():
    if not request.is_json:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    data = request.get_json()
    required_fields = ['name', 'email', 'message']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing {field} field"}), 400
    
    email = data['email']
    #if not is_valid_email(email):
    #    return jsonify({"error": "Invalid email format"}), 400   

    enquiry_filename = os.urandom(5).hex() + ".json"
    #dump_json(data, enquiry_filename)
    create_enquiry_file(enquiry_filename, data)
    
    return jsonify({"message": "Enquiry received", "data": data})

@app.route('/request_demo', methods=['POST'])
def request_demo():
    if not request.is_json:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    data = request.get_json()
    required_fields = ['name', 'email']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing {field} field"}), 400
    
    email = data['email']
    #if not is_valid_email(email):
    #    return jsonify({"error": "Invalid email format"}), 400
    
    demo_request_filename = os.urandom(5).hex() + "_demo.json"
    #dump_json(data, demo_request_filename)
    create_enquiry_file(demo_request_filename, data)
    
    return jsonify({"message": "Demo request received", "data": data})

if __name__ == '__main__':
    app.run(debug=True)
