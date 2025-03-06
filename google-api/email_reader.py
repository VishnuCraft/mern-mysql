from flask import Flask, jsonify, request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
import base64
from bs4 import BeautifulSoup

app = Flask(__name__)

# Define the SCOPES. If modifying it, delete the token.pickle file.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def getEmails():
    creds = None

    # Check for existing credentials
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # Authenticate if necessary
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)

        # Save credentials for next time
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Connect to Gmail API
    service = build('gmail', 'v1', credentials=creds)

    # Fetch messages
    result = service.users().messages().list(userId='me').execute()
    messages = result.get('messages', [])

    email_list = []
    for msg in messages:
        try:
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = txt.get('payload', {})
            headers = payload.get('headers', [])

            # Extract subject and sender
            subject = next((d['value'] for d in headers if d['name'] == 'Subject'), "No Subject")
            sender = next((d['value'] for d in headers if d['name'] == 'From'), "Unknown Sender")

            # Extract email body
            parts = payload.get('parts', [])
            body = ""
            for part in parts:
                if part.get('mimeType') == 'text/html':
                    data = part['body'].get('data', '')
                    data = data.replace("-", "+").replace("_", "/")
                    decoded_data = base64.b64decode(data)
                    soup = BeautifulSoup(decoded_data, "lxml")
                    body = soup.get_text()
                    break

            email_list.append({
                "subject": subject,
                "from": sender,
                "body": body
            })
        except Exception as e:
            email_list.append({"error": str(e)})

    return email_list

@app.route('/emails', methods=['GET'])
def fetch_emails():
    try:
        emails = getEmails()
        return jsonify({"status": "success", "emails": emails})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
