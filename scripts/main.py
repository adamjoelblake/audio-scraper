from bs4 import BeautifulSoup
import requests
import json
import os
from tkinter import Tk
from tkinter import filedialog


# Pseudo Code

    # User input

    # Search known sites until desired book is found

    # Isolate desired audio files from search result
        # Iterate through search result headers and grab first option that contains both title and author

    # Save scraped audio to file


def main():
    bookDict = userBookChoice()
    queryUrl = getQueryUrl(bookDict)
    soup = cookSoup(queryUrl)
    articles = getBookOptions(soup,bookDict)
    selected_index = selectIndex(articles)
    article = chooseBook(articles, selected_index)
    audioFiles = scrapeAudio(article)
    saveFolderPath= selectSaveFolder(bookDict)
    audioRequest(audioFiles,bookDict,saveFolderPath)
    
def getKnownSites():
    with open('knownSites.json', 'r') as file:
        data = json.load(file)
    return data

def userBookChoice():
    title = input('Book Title: ')
    author = input('Author: ')
    queryDict = {'title':title, 'author':author}
    return queryDict

def getQueryUrl(queryDict):
    queryTitle = queryDict.get('title').strip().replace(' ','+')
    queryAuthor = queryDict.get('author').strip().replace(' ','+')
    query = queryTitle + '+' + queryAuthor
    site = getKnownSites().get("dailyAudioBooks")
    searchUrl = site.get('search_url')
    queryUrl = searchUrl + query
    return queryUrl

def cookSoup(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup

def getBookOptions(soup,bookDict):
    bookOptions = {}
    userTitle = bookDict.get('title').lower()
    articles = soup.find('section', id='content').find_all('article')
    for article in articles:
        title = article.find('h2').text
        cleanTitle = title.strip().lower()
        if userTitle in cleanTitle:
            bookOptions[title] = article
    return bookOptions

def selectIndex(options):
    titleOptions = list(options.keys())
    for idx, title in enumerate(titleOptions, start=1):
        print(f"{idx}. {title}")
    while True:
        try:
            choice = int(input("Enter the number of the book you want to select: "))
            if 1 <= choice <= len(titleOptions):
                selected_title = titleOptions[choice-1]
                print(f"You selected: {selected_title}")
                break
            else:
                print(f"Please enter a number between 1 and {len(titleOptions)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    return choice

def chooseBook(options, selection_index):
    titleOptions = list(options.keys())
    selected_title = titleOptions[selection_index - 1]
    return options[selected_title]

def scrapeAudio(article):
    audiofiles= []
    audioURLs= {}
    audioTags = article.find_all('audio')
    for tag in audioTags:
        file = tag.get_text(strip=True)
        audiofiles.append(file)
    for idx, file in enumerate(audiofiles, start=1):
        audioURLs[idx] = file
    return audioURLs

def audioRequest(audioFiles,bookDict,folder):
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

def selectSaveFolder(bookDict):
    bookTitle = bookDict.get('title')
    root = Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory(title="Select a folder to save the audiobook")
    audioBookFolderName = bookTitle.strip().replace(' ','_')
    audioBookFolderPath = os.path.join(folder_selected,audioBookFolderName)
    os.makedirs(audioBookFolderPath)
    return audioBookFolderPath

main()