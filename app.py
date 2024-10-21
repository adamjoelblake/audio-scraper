from flask import Flask, request, jsonify, session, send_file, render_template
from flask_session import Session
from flask_cors import CORS
import zipfile
from io import BytesIO
import os
import main
import requests
import tempfile
import logging
import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler


# Initialize the Flask application
app = Flask(__name__)

# Google Cloud Logging setup
client = google.cloud.logging.Client()
handler = CloudLoggingHandler(client)

# Set up logging
cloud_logger = logging.getLogger("cloudLogger")
cloud_logger.setLevel(logging.INFO) #Hello
cloud_logger.addHandler(handler)

# Example of using cloud logger
cloud_logger.info("Google Cloud Logging is configured and running!")

# Secret key for signing the session data
app.secret_key = 'I_LOVE_READING_BOOKS'

# Session configuration for Google Cloud's server-side storage
app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem for sessions
app.config['SESSION_FILE_DIR'] = '/home/adamjoelblake/audioScraper/sessions'  # Store sessions persistently on your VM
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_THRESHOLD'] = 500  # Limit for the number of sessions to store
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Sessions expire in 1 hour
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True  # Ensure secure cookies over HTTPS

# Ensure the session directory exists
if not os.path.exists(app.config['SESSION_FILE_DIR']):
    os.makedirs(app.config['SESSION_FILE_DIR'])

# Initialize session
Session(app)

# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "*"}},
     supports_credentials=True, 
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Credentials"])

@app.route('/')
def home():
    return render_template('index.html')

# First route: Accepts book title and may request additional input (First half of main function)
@app.route('/scrape', methods=['POST'])
def scrapeBookOptions():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'preflight'}), 200
    
    try:
        # Get user input
        data = request.json
        print(f"Received data: {data}")
        book_title = data.get('title')
        book_author = data.get('author')
        print(f"Book title: {book_title}")
        bookDict = {'title': book_title, 'author': book_author}

        # First half of main function
        print(f"Calling getQueryUrl with {bookDict}")
        queryUrl = main.getQueryUrl(bookDict)
        print(f"Query URL: {queryUrl}")

        print("Calling cookSoup")
        soup = main.cookSoup(queryUrl)
        print("Soup created")

        print("Getting book options")
        bookOptions = main.getBookOptions(soup, bookDict)
        print(f"bookOptions function call successful")
        for option in bookOptions:
            print(bookOptions[option])

        if not bookOptions:
            return jsonify({'error': 'No matching books found!'}), 404

        # Cache the book options
        session['options'] = bookOptions
        print(f"Session options: {session['options'].keys()}")
        session['bookDict'] = bookDict
        print(f"Session bookDict: {session['bookDict']}")

        # Return book options to front end for user to choose
        return jsonify({'bookOptions': bookOptions})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Second route: Accept user's book selection and scrape audio
@app.route('/scrape/continue', methods=['POST'])
def scrapeAudio():
    try:
        data = request.json
        selected_book_index = data.get('selection')
        print(f"Selected book index: {selected_book_index}")
        
        # retrieved cached book options
        bookOptions = session.get('bookOptions')
        print(f"book options: {bookOptions}")
        bookDict = session.get('bookDict')
        print(f"bookDict: {bookDict}")

        if not bookOptions or not bookDict:
            print("Local storage error")
            return jsonify({'error': 'Session expired or no book options available.'}), 400

        # return audio files to front end
        audioFiles = main.chooseBook(bookOptions, selected_book_index)
        session['audioFiles'] = audioFiles
        
        # Print session data for debugging
        print(f"Session Audio Files: {session['audioFiles']}")
        print(f"Session Book Dict: {session['bookDict']}")

        return jsonify({
            'audioFiles': audioFiles,
            'bookTitle': bookDict['title']
        }), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Third route: Download the file from the external source and send it to the client
@app.route('/download_all', methods=['GET'])
def download_audio():
    try:
        bookDict = session.get('bookDict')
        audioFiles = session.get('audioFiles')

        print(f"Session Book Dict: {bookDict}")
        print(f"Session Audio Files: {audioFiles}")
        
        if not bookDict or not audioFiles:
            return jsonify({'error': 'Audio files or bookDict missing from session'}), 400

        # Create a zip file in memory
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for index, file_url in audioFiles.items():
                # download each audio file
                response = requests.get(file_url)
                if response.status_code != 200:
                    return jsonify({'error': f'Failed to download audio file {index}'}), 500

                # Add downloaded content to ZIP
                zip_file.writestr(f"{bookDict['title']}_{index}.mp3", response.content)

        # Ensure the ZIP buffer is set at the beginning of the stream
        zip_buffer.seek(0)

        # Send the ZIP file as a downloadable attachment
        return send_file(zip_buffer, download_name=f"{bookDict['title']}_audiobook.zip", as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)