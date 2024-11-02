from bs4 import BeautifulSoup
import requests
import json
import os
import logging
import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler

# Google Cloud Logging setup
client = google.cloud.logging.Client()
handler = CloudLoggingHandler(client)

# Set up logging
cloud_logger = logging.getLogger("cloudLogger")
cloud_logger.setLevel(logging.INFO) #Hello
cloud_logger.addHandler(handler)

def cookSoup(url):
    cloud_logger.info(f"Cooking soup with url: {url}")
    try:
        cloud_logger.info("trying")
        response = requests.get(url, timeout=10)
        cloud_logger.info(f"Redirect history: {response.history}")
        cloud_logger.info(f"Response status code: {response.status_code}")
        cloud_logger.info(f"Response content (first 100 chars): {response.text[:100]}")
        cloud_logger.info(f"Full response length: {len(response.text)}")
        cloud_logger.info(f"Full response: {response.text}")
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

def getBookOptions(soup,bookDict):
    try:
        bookOptions = {}
        userTitle = bookDict.get('title').lower()
        articles = soup.find('section', id='content').find_all('article')
        for article in articles:
            title = article.find('h2').text
            cleanTitle = title.strip().lower()
            if userTitle in cleanTitle:
                audioUrlDict= scrapeAudio(article)
                bookOptions[title] = audioUrlDict
                # print(f"Book Option Entry: {bookOptions[title]}")
        return bookOptions
    
    except Exception as e:
        print(f"Error in main function getBookOptions: {e}")

def chooseBook(options, selection_index):
    try:
        titleOptions = list(options.keys())
        selected_title = titleOptions[selection_index - 1]
        print(f"Selected Option: {selected_title}")
        return options[selected_title]
    except Exception as e:
        print(f"Error in main function chooseBook: {e}")

def scrapeAudio(entry):
    try:
        audioUrls= {}
        audioTags = entry.find_all('audio')

        count = 1
        for tag in audioTags:
            url = tag.get_text(strip=True)
            audioUrls[count] = url
            count += 1
        return audioUrls
    except Exception as e:
        print(f"Error in main function scrapeAudio: {e}")

def audioRequest(audioFiles,bookDict,folder):
    try:
        title = bookDict.get('title').strip().replace(' ','_')
        for index, url in audioFiles.items():
            # Prepare save file
            file_name = f"{title}_{index:02}.mp3"
            file_path = os.path.join(folder,file_name)

            # Send GET request
            response = requests.get(url, stream=True)
            # Ensure response was recieved
            if response.status_code == 200:
                # Save audio file
                with open(file_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            file.write(chunk)
                print(f"Downloaded {file_name}")
            else:
                print(f"Failed to download {url}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error in main function audioRequest: {e}")

def selectSaveFolder(bookDict):
    try:
        bookTitle = bookDict.get('title').strip().replace(' ', '_')
        folder_selected = '/app/data/'  # Default directory in Heroku
        audioBookFolderPath = os.path.join(folder_selected, bookTitle)
        os.makedirs(audioBookFolderPath, exist_ok=True)
        return audioBookFolderPath
    except Exception as e:
        print(f"Error in main function selectSaveFolder: {e}")

# Pseudo code for searching multiple sites
    # Open 'Known Sites' in app.py and store information locally.
    # Create a list with all query urls from 'Known Sites'
    # Iterate through this list until a book is returned