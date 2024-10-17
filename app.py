from flask import Flask, request, jsonify, session
from flask_session import Session
from flask_cors import CORS
from redis import Redis
import os
import main

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
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
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
CORS(app, resources={r"/*": {"origins": "https://adamjoelblake.github.io"}},
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

        if not bookOptions:
            return jsonify({'error': 'No matching books found!'}), 404
        
        # Cache the book options (use request session or another method for long-term storage)
        session['options'] =  bookOptions
        session['bookDict'] = bookDict
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
        bookOptions = session.get('options')
        print(f"Session book options: {bookOptions}")
        bookDict = session.get('bookDict')
        print(f"Session bookDict: {bookDict}")

        if not bookOptions or not bookDict:
            return jsonify({'error': 'Session expired or no book options available.'}), 400
        
        # return audio files to front end
        audioFiles = main.chooseBook(bookOptions, selected_book_index)
        for idx, file in audioFiles.items():
            print(f"Audio File {idx}: {file}")

        return jsonify({'audioFiles':audioFiles}), 200

    except Exception as e:
        return jsonify({'error':str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)