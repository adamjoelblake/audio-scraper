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

# Pseudo Code

    # User input

    # Search known sites until desired book is found

    # Isolate desired audio files from search result
        # Iterate through search result headers and grab first option that contains both title and author

    # Save scraped audio to file


# def main():
#     bookDict = userBookChoice()
#     queryUrl = getQueryUrl(bookDict)
#     soup = cookSoup(queryUrl)
#     articles = getBookOptions(soup,bookDict)
#     selected_index = selectIndex(articles)
#     article = chooseBook(articles, selected_index)
#     audioFiles = scrapeAudio(article)
#     for idx, file in audioFiles.items():
#         print(f"{idx}. {file}")
    # saveFolderPath= selectSaveFolder(bookDict)
    # audioRequest(audioFiles,bookDict,saveFolderPath)
    
def getKnownSites():
    try:
        with open('knownSites.json', 'r') as file:
            data = json.load(file)
        return data
    except Exception as e:
        print(f"Error in main function getKnownSites: {e}")

# def userBookChoice():
#     title = input('Book Title: ')
#     author = input('Author: ')
#     queryDict = {'title':title, 'author':author}
#     return queryDict

def getQueryUrl(queryDict):
    try:
        queryTitle = queryDict.get('title').strip().replace(' ','+')
        if queryDict.get('author'):
            queryAuthor = queryDict.get('author').strip().replace(' ','+')
            query = queryTitle + '+' + queryAuthor      
        query = queryTitle
        # cloud_logger.info(f"Query: {query}")
        site = getKnownSites().get("dailyAudioBooks")
        # cloud_logger.info(f"Site: {site}")
        searchUrl = site.get('search_url')
        queryUrl = searchUrl + query
        # cloud_logger.info(f"Query Url: {queryUrl}")
        return queryUrl
    except Exception as e:
        cloud_logger.info(f"Error in main function getQueryUrl: {e}")

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

# def selectIndex(options):
#     titleOptions = list(options.keys())
#     for idx, title in enumerate(titleOptions, start=1):
#         print(f"{idx}. {title}")
#     while True:
#         try:
#             choice = int(input("Enter the number of the book you want to select: "))
#             if 1 <= choice <= len(titleOptions):
#                 selected_title = titleOptions[choice-1]
#                 print(f"You selected: {selected_title}")
#                 break
#             else:
#                 print(f"Please enter a number between 1 and {len(titleOptions)}.")
#         except ValueError:
#             print("Invalid input. Please enter a number.")
#     return choice

def chooseBook(options, selection_index):
    try:
        titleOptions = list(options.keys())
        selected_title = titleOptions[selection_index - 1]
        print(f"Selected Option: {selected_title}")
        return options[selected_title]
    except Exception as e:
        print(f"Error in main function chooseBook: {e}")

def scrapeAudio(article):
    try:
        audioUrls= {}
        audioTags = article.find_all('audio')

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

# main()