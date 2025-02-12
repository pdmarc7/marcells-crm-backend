from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
import io
import os

# Replace with your service account credentials file path
SERVICE_ACCOUNT_FILE = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))

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

