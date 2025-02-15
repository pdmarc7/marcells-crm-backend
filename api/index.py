from flask import Flask, jsonify, request, render_template_string
import json, os, re

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload

from google.oauth2 import service_account
from googleapiclient.errors import HttpError

import io
import os
import base64
import tempfile

# Decode the base64-encoded service account JSON
json_str = base64.b64decode(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")).decode()

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

# Write the JSON to a temporary file
with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
    temp_file.write(json_str.encode())
    temp_file_path = temp_file.name  # Store file path

# Authenticate using service account
creds = service_account.Credentials.from_service_account_file(
    temp_file_path, scopes=SCOPES
)

# Optional: Clean up the file after use
os.unlink(temp_file_path)

# Build the Drive API service
service = build('drive', 'v3', credentials=creds)
'''
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
'''

ENQUIRY_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Exciting Enquiry Alert!</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Rubik:ital,wght@0,300..900;1,300..900&family=Sarala:wght@400;700&display=swap" rel="stylesheet">
    <style>
        .sarala-regular {
          font-family: "Sarala", serif;
          font-weight: 400;
          font-style: normal;
        }

        .sarala-bold {
          font-family: "Sarala", serif;
          font-weight: 700;
          font-style: normal;
        }


        .rubik-regular {
          font-family: "Rubik", serif;
          font-optical-sizing: auto;
          font-weight: 400;
          font-style: normal;
        }

        body {
            font-family: 'Sarala', sans-serif;
        }
        .email-container {
            max-width: 600px;
            margin: auto;
            background-color: #ffffff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .header {
            background-color: #007bff;
            color: #ffffff;
            padding: 15px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }
        .content {
            padding: 20px;
            font-size: 16px;
            color: #333;
        }
        .btn-primary {
            display: block;
            width: fit-content;
            margin: 20px auto;
            text-decoration: none;
            padding: 10px 20px;
            background-color: #007bff;
            color: #ffffff;
            border-radius: 5px;
            font-weight: bold;
        }
        .footer {
            text-align: center;
            font-size: 14px;
            color: #666;
            padding: 15px;
        }
    </style>
</head>
<body>
    <h1 class="">{{ business_id }}</h1> 
    {% if notification_type == "demo" %}
    <h4>Request For Demo</h4>
    {% else %}
    <h4>ENQUIRY</h4>
    {% endif %}
    <p><strong>From:</strong> {{ sender_name }} ({{ sender_email }}) </p>
    {% if notification_type == "enquiry" %}
    <p>{{ message }}</p>
    {% endif %}
    </div>
</body>
</html>

'''

def download_json_from_drive(service, file_id):
    """Downloads a JSON file from Google Drive and returns it as a dict."""
    request = service.files().get_media(fileId=file_id)
    file_stream = io.BytesIO()
    downloader = MediaIoBaseDownload(file_stream, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    file_stream.seek(0)
    return json.loads(file_stream.read().decode("utf-8"))


def send_email(subject, body, to_email, is_html=False):
    """
    Sends an email with optional HTML formatting.

    Args:
        subject (str): Email subject.
        body (str): Email body (can be plain text or HTML).
        to_email (str): Recipient's email address.
        is_html (bool): If True, sends an HTML email; otherwise, plain text.
    """
    # File ID from Google Drive link
    FILE_ID = os.getenv("CONFIG_FILE_ID")
    mail_config = download_json_from_drive(service, FILE_ID)

    sender_email = mail_config['email']
    sender_password = mail_config["app_password"]
    
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject

    # Attach message body as HTML or plain text
    msg.attach(MIMEText(body, "html" if is_html else "plain"))

#    try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()  # Upgrade to secure connection
    server.login(sender_email, sender_password)  # Authenticate

    server.sendmail(sender_email, to_email, msg.as_string())
    server.quit()
#        print("Email sent successfully.")
#    except Exception as e:
#        print(f"Error sending email: {e}")


def create_enquiry_file(filename, enquiry, demo=False):
    #enquiry_json = json.dumps(enquiry)
    if demo:
        subject = f"Demo Request From {enquiry['name']} - {enquiry['business_id']}"

    else:
        subject = f"Enquiry From {enquiry['name']} - {enquiry['business_id']}"

    if demo:
        body = render_template_string(ENQUIRY_TEMPLATE, business_id = enquiry['business_id'], sender_name=enquiry['name'], sender_email=enquiry['email'], notification_type="demo")
    else:
        body = render_template_string(ENQUIRY_TEMPLATE, business_id = enquiry['business_id'], sender_name=enquiry['name'], sender_email=enquiry['email'], message = enquiry['message'], notification_type="enquiry")
    
    send_email(subject, body, "marcellsdave0@gmail.com", is_html=True)

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

def update_file_in_drive(service, file_id, json_data):
    """Uploads JSON data directly to Google Drive without writing to disk."""
    json_bytes = json.dumps(json_data, indent=4).encode("utf-8")
    json_stream = io.BytesIO(json_bytes)
    
    media = MediaIoBaseUpload(json_stream, mimetype="application/json", resumable=True)
    updated_file = service.files().update(fileId=file_id, media_body=media).execute()
    
    return updated_file

@app.route('/subscribe_mail', methods=['POST'])
def add_to_mailinglist():
    MAILINGLIST_FILE_ID = os.getenv("MAILING_LIST_FILE_ID")
    mailinglist = download_json_from_drive(service, MAILINGLIST_FILE_ID)
    
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

    update_file_in_drive(service, MAILINGLIST_FILE_ID, waitlist)
    
    return jsonify({"message": "OK", "email": email}), 200

@app.route('/add_to_waitlist', methods=['POST'])
def add_to_waitlist():
    WAITLIST_FILE_ID = os.getenv("WAITLIST_FILE_ID")
    waitlist = download_json_from_drive(service, WAITLIST_FILE_ID)
    
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

    update_file_in_drive(service, WAITLIST_FILE_ID, waitlist)
    
    return jsonify({"message": "OK", "email": email}), 200

@app.route('/remove_from_waitlist', methods=['POST'])
def remove_from_waitlist():
    WAITLIST_FILE_ID = os.getenv("WAITLIST_FILE_ID")
    waitlist = download_json_from_drive(service, WAITLIST_FILE_ID)
    
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
    update_file_in_drive(service, WAITLIST_FILE_ID, waitlist)
    
    return jsonify({"message": "Removed", "email": email}), 200

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
    
    return jsonify({"message": "Enquiry received", "data": data}), 200

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
    create_enquiry_file(demo_request_filename, data, demo=True)
    
    return jsonify({"message": "Demo request received", "data": data}), 200

if __name__ == '__main__':
    app.run(debug=True)
