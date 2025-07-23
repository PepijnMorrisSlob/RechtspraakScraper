from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
import os

# Path to your credentials file
SERVICE_ACCOUNT_FILE = 'vendo-veritas-innovation-9c38dadb3116.json'
# The folder ID you want to upload to
FOLDER_ID = '1ZI7Uiajo5VV_4PyGfhxCtcC9bkdEW82c'
# The file you want to upload (change as needed)
FILE_TO_UPLOAD = 'test_upload.txt'

# Create a test file to upload
with open(FILE_TO_UPLOAD, 'w', encoding='utf-8') as f:
    f.write('This is a test upload to Google Drive.')

# Authenticate and build the Drive service
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=['https://www.googleapis.com/auth/drive.file']
)
service = build('drive', 'v3', credentials=creds)

# Upload the file
file_metadata = {
    'name': os.path.basename(FILE_TO_UPLOAD),
    'parents': [FOLDER_ID]
}
media = MediaFileUpload(FILE_TO_UPLOAD, resumable=True)
file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
print(f"Uploaded file with ID: {file.get('id')}") 