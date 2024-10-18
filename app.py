from flask import Flask, request, jsonify, session, send_file
from flask_session import Session
from flask_cors import CORS
from redis import Redis
import zipfile
from io import BytesIO
import os
import main
import requests

# Initialize the Flask application
app = Flask(__name__)

# Secret key for signing the session data
app.secret_key = 'I_LOVE_READING_BOOKS'

# Session configuration for server-side storage
redis_url = os.environ.get('REDISCLOUD_URL', 'redis://localhost:6379')  # Default to localhost if Redis URL isn't available
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = Redis.from_url(redis_url)
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'audiobook-scraper-session:'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Sessions expire in 1 hour
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True

try:
    redis_conn = Redis.from_url(redis_url)
    redis_conn.ping()  # This sends a ping to verify Redis is connected
    print("Redis connection successful")
except Exception as e:
    print(f"Redis connection error: {e}")

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
        # Return 200 for preflight OPTIONS requests
        return jsonify({'status': 'preflight'}), 200
    
    try:
        # Get user input
        data = request.json
        print(f"Received data: {data}")
        book_title = data.get('title')
        book_author = data.get('author')
        print(f"Book title: {book_title}")
        bookDict = {'title':book_title, 'author':book_author}

    
        # First half of main function
        print(f"Calling getQueryUrl with {bookDict}")
        queryUrl = main.getQueryUrl(bookDict)
        print(f"Query URL: {queryUrl}")

        print("Calling cookSoup")
        soup = main.cookSoup(queryUrl)
        print("Soup created")

        print("Getting book options")
        # book Opitons is a dictionary stored as {Entry tile: audiofiles{index:audio file url}}
        bookOptions = main.getBookOptions(soup,bookDict)
        print(f"bookOptions function call successful")
        for option in bookOptions:
            print(option)

        if not bookOptions:
            return jsonify({'error': 'No matching books found!'}), 404
        
        # Cache the book options (use request session or another method for long-term storage)
        session['options'] =  bookOptions
        print(f"Session options: {session['options'].keys()}")
        session['bookDict'] = bookDict
        print(f"Session bookDict: {session['bookDict']}")
        #print(f"Session after setting: {dict(session)}")


        # Return book options to front end for user to choose
        return jsonify({'bookOptions': list(bookOptions.keys())})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Second route: Accept user's book selection and scrape audio (Second half of main)
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
        # for idx, file in audioFiles.items():
        #     print(f"Audio File {idx}: {file}")

        return jsonify({
            'audioFiles':audioFiles,
            'bookTitle':bookDict['title']
            }), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error':str(e)}), 500

# Third route: Download the file from the external source and send it to the client
@app.route('/download_all', methods=['GET'])
def download_audio():
    try:
        bookTitle = session.get('bookDict').get('title')
        audioFiles = session.get('audioFiles')

        # Create a zip file in memory
        zip_buffer = BytesIO()

        # Create a zip file in memory
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for index, file_url in audioFiles.items():
                #download each audio file
                response = requests.get(file_url)
                if response.status_code != 200:
                    return jsonify({'error':f'Failed to download audio file {index}'}), 500
                
                # Add downloaded content to ZIP
                zip_file.writestr(f"{bookTitle}_{index}.mp3", response.content)

        # Ensure the ZIP buffer is set at the beginning of the stream
        zip_buffer.seek(0)

        # Send the ZIP file as a downloadable attachment
        return send_file(zip_buffer, download_name=f"{bookTitle}_audiobook.zip", as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)