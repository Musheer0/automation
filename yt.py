import os
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Environment Variables
TOKEN_PATH = os.getenv("TOKEN_PATH", "token.json")
CLIENT_SECRET_PATH = os.getenv("CLIENT_SECRET_PATH", "client.json")
DEFAULT_CATEGORY_ID = os.getenv("DEFAULT_CATEGORY_ID", "22")

def authenticate():
    """Authenticate and return credentials, reusing stored tokens if available."""
    creds = None

    # Load existing credentials if available
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # Check if credentials are expired and refresh them
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())  # Refresh token without login prompt
            print("🔄 Token refreshed successfully!")
        except Exception as e:
            print(f"⚠️ Token refresh failed: {e}")
            creds = None  # Force re-authentication if refresh fails

    # If no valid credentials, request login (only runs once)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
        creds = flow.run_local_server(port=5000)

    # Save credentials to TOKEN_PATH for future use
    with open(TOKEN_PATH, "w") as token_file:
        token_file.write(creds.to_json())

    return creds

def upload_video(video_file, title, description, tags, category_id=None, privacy_status="public"):
    """Uploads a video to YouTube."""
    credentials = authenticate()
    youtube = build("youtube", "v3", credentials=credentials)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title.strip()[:100],
                "description": description,
                "tags": tags,
                "categoryId": category_id or DEFAULT_CATEGORY_ID  # Use env var if no category is provided
            },
            "status": {
                "privacyStatus": privacy_status,
                "madeForKids": False  # Explicitly set audience as 'Not made for kids'
            }
        },
        media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True)
    )

    response = request.execute()
    print(f"✅ Upload Successful! Video ID: {response['id']}")
    return response['id']
