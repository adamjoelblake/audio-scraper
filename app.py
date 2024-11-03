from flask import Flask, request, jsonify, session, send_file, render_template, Response
from flask_session import Session
from flask_cors import CORS
import zipfile
from io import BytesIO
from bs4 import BeautifulSoup
import os
import json
import requests
import tempfile
import logging
import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler
from google.cloud import storage


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

# Initialize Google Cloud Storage
storage_client = storage.Client()
bucket_name = 'audiobook-bucket-22/'

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

# Known site information
def getKnownSites():
    try:
        with open('knownSites.json', 'r') as file:
            data = json.load(file)
        return data
    except Exception as e:
        cloud_logger.info(f"Error in main function getKnownSites: {e}")
knownSitesJson = getKnownSites()
siteNames = knownSitesJson.keys()

@app.route('/')
def home():
    return render_template('index.html')

# First route: Accepts book title and may request additional input (First half of main function)
@app.route('/scrape', methods=['POST'])
def scrapeBookOptions():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'preflight'}), 200

    # Get user input
    data = request.json
    cloud_logger.info(f"Received data: {data}")
    book_title = data.get('title')
    book_author = data.get('author')
    cloud_logger.info(f"Book title: {book_title}")
    bookDict = {'title': book_title, 'author': book_author}

    # First half of main function
    for site in siteNames:
        cloud_logger.info(f"Calling getQueryUrl with {bookDict}")
        queryUrl = getQueryUrl(site, bookDict)
        cloud_logger.info(f"Query URL: {queryUrl}")

        cloud_logger.info("Calling cookSoup")
        soup = cookSoup(queryUrl)
        cloud_logger.info(f"Soup created: {soup}")

        cloud_logger.info("Getting book options")
        bookOptions = getBookOptions(soup, bookDict, site)
        for book in bookOptions:
            cloud_logger.info(f"Entry Title: {book}")
        
        if bookOptions:
            # Cache the book options
            cloud_logger.info(f"Storing data locally")
            try:
                session['bookOptions'] = bookOptions
            except Exception as e:
                cloud_logger.info(f"Unable to store bookOptions locally.")
            try:
                session['bookDict'] = bookDict
            except Exception as e:
                cloud_logger.info(f"Unable to store bookDict locally.")
            try:
                session['site'] = site
            except Exception as e:
                cloud_logger.info(f"Unable to store site locally.")
            
            # Return book options to front end for user to choose
            return jsonify({'bookOptions': bookOptions})

    if not bookOptions:
        return jsonify({'error': 'No matching books found!'}), 404

# Second route: Accept user's book selection and scrape audio
@app.route('/scrape/continue', methods=['POST'])
def scrapeAudio():
    try:
        data = request.json
        selected_book_index = data.get('selection')
        cloud_logger.info(f"Selected book index: {selected_book_index}")
        
        # retrieved cached book options
        bookOptions = session.get('bookOptions')
        cloud_logger.info(f"book options: {bookOptions}")
        bookDict = session.get('bookDict')
        cloud_logger.info(f"bookDict: {bookDict}")
        site = session.get('site')
        cloud_logger.info(f"Site: {site}")

        if not bookOptions or not bookDict:
            cloud_logger.info("Local storage error")
            return jsonify({'error': 'Session expired or no book options available.'}), 400


        # return audio files to front end
        audioFiles = chooseBook(bookOptions, selected_book_index)
        session['audioFiles'] = audioFiles
        
        # cloud_logger.info session data for debugging
        cloud_logger.info(f"Session Audio Files: {session['audioFiles']}")
        cloud_logger.info(f"Session Book Dict: {session['bookDict']}")

        return jsonify({
            'audioFiles': audioFiles,
            'bookTitle': bookDict['title']
        }), 200

    except Exception as e:
        cloud_logger.info(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Third route: Download the file from the external source and send it to the client
@app.route('/download_all', methods=['GET'])
def download_audio():
    cloud_logger.info(f"Downloading audio")

    bookDict = session.get('bookDict')
    audioFiles = session.get('audioFiles')

    cloud_logger.info(f"Session Book Dict: {bookDict}")
    cloud_logger.info(f"Session Audio Files: {audioFiles}")
    
    if not bookDict or not audioFiles:
        return jsonify({'error': 'Audio files or bookDict missing from session'}), 400

    def generate():
        with BytesIO() as zip_buffer:
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED ) as zip_file:
                try:
                    for index, file_url in audioFiles.items():
                        # download each audio file
                        cloud_logger.info(f"Attempting to download file at URL: {file_url}")
                        response = requests.get(file_url, stream=True)
                        if response.status_code == 200:
                            zip_file.writestr(f"{bookDict['title']}_{index}.mp3", response.content)
                            cloud_logger.info(f"Successfully downloaded file {index}")
                        else:
                            cloud_logger.error(f"Failed to download file {index} with status {response.status_code}")
                except Exception as e:
                    cloud_logger.error(f"Failed to download file {index} with status {response.status_code}")
            
            zip_buffer.seek(0)
            while True:
                chunk = zip_buffer.read(4096)
                if not chunk:
                    break
                yield chunk
    
    response = Response(generate(), mimetype='application/octet-stream')
    response.headers['Content-Disposition'] = f'attachment; filename="{bookDict["title"]}_audiobook.zip"'
    response.headers['Content-Type'] = 'application/octet-stream'
    return response

def getQueryUrl(site, queryDict):
    try:
        queryTitle = queryDict.get('title').strip().replace(' ','+')
        if queryDict.get('author'):
            queryAuthor = queryDict.get('author').strip().replace(' ','+')
            query = queryTitle + '+' + queryAuthor      
        query = queryTitle
        siteDict = knownSitesJson.get(site)
        searchUrl = siteDict.get('search_url')
        queryUrl = searchUrl + query
        return queryUrl
    except Exception as e:
        cloud_logger.info(f"Error in main function getQueryUrl: {e}")

def getBookOptions(soup, bookDict, site):
    # Site navigation information
    navigation = knownSitesJson.get(site).get("html_navigation")
    section_tag = navigation.get("query_results_section")
    section_id = navigation.get("query_results_id")
    entry_tag = navigation.get("entry")
    entry_title_tag = navigation.get("entry_title")
    audio_tag = navigation.get("audio_tag")
    audio_file_tag = navigation.get("file_tag")

    cloud_logger.info(f"Getting book options for {site}")
    try:
        bookOptions = {}
        userTitle = bookDict.get('title').lower()
        entries = soup.find(section_tag, id=section_id).find_all(entry_tag)
        for entry in entries:
            title = entry.find(entry_title_tag).text
            cleanTitle = title.strip().lower()
            if userTitle in cleanTitle:
                audioUrlDict= scrapeAudio(entry, audio_tag)
                bookOptions[title] = audioUrlDict
        return bookOptions
    
    except Exception as e:
        cloud_logger.info(f"Error in main function getBookOptions: {e}")

def chooseBook(options, selection_index):
    try:
        titleOptions = list(options.keys())
        selected_title = titleOptions[selection_index - 1]
        cloud_logger.info(f"Selected Option: {selected_title}")
        return options[selected_title]
    except Exception as e:
        cloud_logger.info(f"Error in main function chooseBook: {e}")

def scrapeAudio(entry, audio_tag):
    try:
        audioUrls= {}
        audio_section = entry.find_all(audio_tag)

        count = 1
        for audio in audio_section:
            url = audio.get('src')
            if not url:
                
                source = audio.find('source')
                url = source['src'] if source and source.has_attr('src') else None
            audioUrls[count] = url
            count += 1
        return audioUrls
    
    except Exception as e:
        cloud_logger.info(f"Error in main function scrapeAudio: {e}")

def cookSoup(url):
    cloud_logger.info(f"Cooking soup with url: {url}")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            try:
                cloud_logger.info("Attempting to parse with BeautifulSoup...")
                soup = BeautifulSoup(response.text, 'html.parser')
                if not soup or len(soup) == 0:
                    cloud_logger.error("Soup object is empty or None. The page might be malformed.")
                else:
                    # Optionally, check for specific tags
                    title_tag = soup.find('title')
                    if title_tag:
                        cloud_logger.info(f"Page title: {title_tag.string}")
                        return soup
                    else:
                        cloud_logger.error("No title tag found in the parsed HTML.")
                        cloud_logger.info(f"Parsed content preview: {soup.prettify()[:500]}")
                        return soup
            except:
                cloud_logger.info(f"Failed to retrieve the page, status code: {response.status_code}")
                return None
        else:
            cloud_logger.info(f"Failed to retrieve the page, status code: {response.status_code}")
            return None
    except Exception as e:
        cloud_logger.info(f"Error in main function cookSoup: {e}")

if __name__ == '__main__':
    app.run(debug=True)