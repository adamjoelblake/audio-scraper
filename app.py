from flask import Flask, request, jsonify, session, send_file
from flask_session import Session
from flask_cors import CORS
import zipfile
from io import BytesIO
import os
import main
import requests

# Initialize the Flask application
app = Flask(__name__)

# Secret key for signing the session data
app.secret_key = 'I_LOVE_READING_BOOKS'

# Session configuration for Heroku's server-side storage
app.config['SESSION_TYPE'] = 'filesystem'  # Use Heroku's ephemeral file system
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'  # Store session data in the /tmp directory on Heroku
app.config['SESSION_FILE_THRESHOLD'] = 500  # Limit for number of sessions to store
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Sessions expire in 1 hour
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False

# Initialize session
Session(app)

# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "*"}},
     supports_credentials=True, 
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Credentials"])

@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Audiobook Scraper API"})

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
        bookOptions = data.get('bookOptions')
        print(f"Local book options: {bookOptions}")
        bookDict = data.get('bookDict')
        print(f"Local bookDict: {bookDict}")

        if not bookOptions or not bookDict:
            print("Local storage error")
            return jsonify({'error': 'Session expired or no book options available.'}), 400

        # return audio files to front end
        audioFiles = main.chooseBook(bookOptions, selected_book_index)
        session['audioFiles'] = audioFiles
        session['bookDict'] = bookDict
        
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