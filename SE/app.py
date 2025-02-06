from flask import Flask, redirect, url_for, session, request, send_from_directory, jsonify, render_template, flash
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import os
import io
import google.auth
from google.auth.transport.requests import Request
from cryptography.fernet import Fernet
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management
app.config['SESSION_COOKIE_NAME'] = 'your_session_cookie'

# Folder paths
UPLOAD_FOLDER = 'server_files'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# TEMP_FOLDER = 'temp'
LOG_FILE = 'download_log.txt'
# KEY_FILE = 'key.key'

# The OAuth 2.0 credentials file you downloaded from Google Developer Console
CLIENT_SECRETS_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Flask route to start OAuth authentication
@app.route('/login')
def login():
    # Flow for OAuth authentication
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    
    # Store the state in the session to validate in the callback
    session['state'] = state
    return redirect(authorization_url)

# OAuth callback route
@app.route('/oauth2callback')
def oauth2callback():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES, state=session['state'])
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    
    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)
    
    return redirect(url_for('index'))

# Helper function to convert credentials to a dictionary
def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

# Check if the user is logged in with valid credentials
def get_credentials():
    credentials = None
    if 'credentials' in session:
        credentials = google.auth.credentials.Credentials.from_authorized_user_info(session['credentials'])
    if not credentials or credentials.expired or credentials is None:
        return None
    return credentials

# Route for the home page
@app.route('/')
def index():
    credentials = get_credentials()
    if credentials is None:
        return redirect(url_for('login'))
    
    # Build the Google Drive API client
    drive_service = build('drive', 'v3', credentials=credentials)
    
    # List files in the Google Drive account
    results = drive_service.files().list(pageSize=10, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    return render_template('index.html', files=items)


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123"

# Ensure necessary folders exist
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# os.makedirs(TEMP_FOLDER, exist_ok=True)

# Load or generate the encryption key
# if os.path.exists(KEY_FILE):
#     with open(KEY_FILE, 'rb') as key_file:
#         key = key_file.read()
# else:
#     key = Fernet.generate_key()
#     with open(KEY_FILE, 'wb') as key_file:
#         key_file.write(key)

# cipher = Fernet(key)

# @app.route('/')
# def index():
#     """Render the main page with options: Upload, Download, and View Log."""
#     return render_template('index.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    """Handle Admin Login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True  # Set session
            flash("Login Successful", "success")
            return redirect(url_for('upload_page'))
        else:
            flash("Invalid Credentials", "danger")

    return render_template('admin_login.html')

@app.route('/admin-logout')
def admin_logout():
    """Log out the admin"""
    session.pop('admin', None)
    flash("Logged Out Successfully", "info")
    return redirect(url_for('index'))


@app.route('/upload-page')
def upload_page():
    """Render the upload page only if admin is logged in."""
    if 'admin' not in session:
        flash("Please log in as Admin to upload files", "warning")
        return redirect(url_for('admin_login'))

    return render_template('upload_page.html')

# Route to upload file to Google Drive
@app.route('/upload', methods=['POST'])
def upload_file():
    credentials = get_credentials()
    if credentials is None:
        return redirect(url_for('login'))
    
    drive_service = build('drive', 'v3', credentials=credentials)
    
    # Handle file upload
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    
    if file.filename == '':
        return "No selected file", 400
    
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    
    media = MediaFileUpload(file_path, mimetype='application/octet-stream', resumable=True)
    file_metadata = {'name': file.filename}
    
    # Upload the file to Google Drive
    drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    
    # Remove the temporary file
    os.remove(file_path)
    
    return redirect(url_for('index'))

# @app.route('/upload', methods=['POST'])
# def upload_file():
#     """Handle file upload, encrypt it, and save to the server."""
#     if 'admin' not in session:
#         return jsonify({"error": "Unauthorized"}), 403

#     if 'file' not in request.files:
#         return "No file part", 400
#     file = request.files['file']
#     if file.filename == '':
#         return "No selected file", 400

#     # Read file and encrypt it
#     file_data = file.read()
#     encrypted_data = cipher.encrypt(file_data)

#     # Save the encrypted file
#     encrypted_file_path = os.path.join(UPLOAD_FOLDER, file.filename)
#     with open(encrypted_file_path, 'wb') as f:
#         f.write(encrypted_data)

#     flash("File uploaded successfully!", "success")
#     return redirect(url_for('upload_page'))

@app.route('/download-page')
def download_page():
    """Render the download page."""
    return render_template('download_page.html')

@app.route('/files', methods=['GET'])
def list_files():
    """Return a list of available files for download."""
    files = []
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            files.append({"name": filename, "size": os.path.getsize(file_path)})
    return jsonify(files)

# Route to download a file from Google Drive
@app.route('/download/<file_id>')
def download_file(file_id):
    credentials = get_credentials()
    if credentials is None:
        return redirect(url_for('login'))
    
    drive_service = build('drive', 'v3', credentials=credentials)
    
    # Request file metadata
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.FileIO(os.path.join(UPLOAD_FOLDER, 'downloaded_file'), 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    
    return send_from_directory(UPLOAD_FOLDER, 'downloaded_file', as_attachment=True)

# @app.route('/download/<filename>')
# def download_file(filename):
#     """Decrypt and allow the user to download a file."""
#     encrypted_file_path = os.path.join(UPLOAD_FOLDER, filename)
#     if not os.path.exists(encrypted_file_path):
#         return "File not found", 404

#     decrypted_file_path = os.path.join(TEMP_FOLDER, filename)
#     with open(encrypted_file_path, 'rb') as f:
#         encrypted_data = f.read()
#     with open(decrypted_file_path, 'wb') as f:
#         f.write(cipher.decrypt(encrypted_data))

#     # Log the download (exclude microseconds)
#     with open(LOG_FILE, 'a') as log:
#         log.write(f"{filename}\t{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

#     # Send the decrypted file for download
#     response = send_file(decrypted_file_path, as_attachment=True)
    
#     # Optionally delete the temporary file after sending it
#     #os.remove(decrypted_file_path)
    
#     return response



@app.route('/view-log-page')
def view_log_page():
    """Render the view log page."""
    if 'admin' not in session:
        flash("Please log in as Admin to view logs", "warning")
        return redirect(url_for('admin_login'))

    return render_template('view_log_page.html')

@app.route('/download-log', methods=['GET'])
def download_log():
    """Provide the download log entries in JSON format."""
    if not os.path.exists(LOG_FILE):
        return jsonify([])  # Return empty list if no log file exists

    logs = []
    with open(LOG_FILE, 'r') as log:
        for line in log:
            parts = line.strip().split(' downloaded on ')
            if len(parts) == 2:
                filename, timestamp = parts
                logs.append({"filename": filename, "timestamp": timestamp})

    return jsonify(logs)


@app.route('/download-success/<filename>', methods=['POST'])
def download_success(filename):
    """Log the download and show a success message."""
    with open(LOG_FILE, 'a') as log:
        log.write(f"{filename} downloaded on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    return jsonify({"message": "Download logged successfully"}), 200


if __name__ == '__main__':
    app.run(debug=True)