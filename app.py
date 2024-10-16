from flask import Flask, request, jsonify
from flask_cors import CORS
import main

# Initialize the Flask application
app = Flask(__name__)

# Enable CORS for all routes
CORS(app, resources={r"/*": {
    "origins": "https://adamjoelblake.github.io",
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type"]
}})

book_options_cache = {}

@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Audiobook Scraper API"})

# First route: Accepts book title and may request additional input (First half of main function)
@app.route('/scrape', methods=['POST'])
def scrapeBookOptions():
    if request.method == 'OPTIONS':
        # Return 200 for preflight OPTIONS requests
        return '', 200
    
    # Get user input
    data = request.json
    book_title = data.get('title')
    book_author = data.get('author')
    bookDict = {'title':book_title, 'author':book_author}

    try:
        # First half of main function
        queryUrl = main.getQueryUrl(bookDict)
        soup = main.cookSoup(queryUrl)
        articles = main.getBookOptions(soup,bookDict)

        if not articles:
            return jsonify({'error': 'No matching books found!'}), 404
        
                
        # Cache the book options (use request session or another method for long-term storage)
        book_options_cache['options'] =  articles
        book_options_cache['bookDict'] = bookDict

        # Return book options to front end for user to choose
        return jsonify({'bookOptions': list(articles.keys())})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Second route: Accept user's book selection and scrape audio (Second half of main)
@app.route('/scrape/continue', methods=['POST'])
def scrapeAudio():
    data = request.json
    selected_book_index = int(data.get('selection'))

    try:
        # retrieved cached book options
        bookOptions = book_options_cache.get('options')
        bookDict = book_options_cache.get('bookDict')

        if not bookOptions or not bookDict:
            return jsonify({'error': 'Session expired or no book options available.'}), 400
        
        # Get the selected book article and scrape audio files
        selected_article = main.chooseBook(bookOptions, selected_book_index)
        audioFiles = main.scrapeAudio(selected_article)

        return jsonify({'audioFiles':audioFiles}), 200

    except Exception as e:
        return jsonify({'error':str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)