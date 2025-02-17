import requests
import httpx
import os
import asyncio
import random
import re
from yt import upload_video
from flask import Flask, jsonify, request
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# Instagram API Credentials
INSTAGRAM_BASE = os.getenv("INSTAGRAM_BASE_URL", "https://graph.instagram.com")
USER_ID = os.getenv("INSTAGRAM_USER_ID")
TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
ADMINS = os.getenv("ADMINS", "").split(",")

# Video Upload Settings
CATEGORY_IDS = os.getenv("DEFAULT_CATEGORY_IDS", "").split(",")
CATEGORY_IDS = [cat for cat in CATEGORY_IDS if cat]  # Remove empty strings

# Replies and errors
REPLIES = [{"text": 'downloading reel'}, {"text": 'uploading reel'}, {"text": 'deleting reel'}]
ERROR_MESSAGE = {"text": "error downloading reel"}

app = Flask(__name__)

def extract_hashtags(text):
    """Extracts hashtags from a given text."""
    return re.findall(r"#\w+", text)

def download(url, filename):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(1024):
                print("Downloading chunk...")
                file.write(chunk)
        print("Download completed")
    else:
        print(f"Download failed with status code: {response.status_code}")

def delete_reel(file_id):
    file_path = f"{file_id}.mp4"
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted file: {file_path}")
    else:
        print("File not found")

async def send_message(recipient_id, message):
    url = f"{INSTAGRAM_BASE}/v22.0/{USER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "recipient": {"id": recipient_id},
        "message": message
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        return response.json()

@app.route('/webhook', methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return request.args.get("hub.challenge", "")

    if request.method == "POST":
        body = request.json
        entry = body.get("entry", [{}])[0]
        messaging = entry.get("messaging", [{}])[0]
        sender = messaging.get("sender", {}).get("id")

        if not sender or sender not in ADMINS:
            return jsonify({"error": "Unauthorized or missing sender"}), 403

        message = messaging.get("message", {})
        attachments = message.get("attachments", [])

        if attachments and attachments[0]["type"] == "ig_reel":
            reel = attachments[0]["payload"]
            reel_id = reel.get('reel_video_id')
            title = reel.get('title', 'Untitled Reel')
            url = reel.get('url')

            if reel_id and url:
                filename = f"{reel_id}.mp4"
                download(url, filename)

                tags = extract_hashtags(title)
                video_id = upload_video(
                    video_file=filename,
                    title=title,
                    description='nothing...',
                    category_id=random.choice(CATEGORY_IDS) if CATEGORY_IDS else "22",  # Default category
                    privacy_status="public",
                    tags=['reel'] + tags
                )

                delete_reel(reel_id)

                # Notify user
                asyncio.run(send_message(sender, {"text": f"Uploaded video: https://www.youtube.com/watch?v={video_id}"}))
                asyncio.run(send_message(sender, REPLIES[2]))

                return jsonify({"status": "success", "video_id": video_id})

    return jsonify({"error": "Invalid request"}), 400

if __name__ == "__main__":
    app.run(debug=True)
