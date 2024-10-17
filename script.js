// Function to handle the book search form submission
let audioFiles = {};
let bookTitle = '';

function searchBooks(event) 
{
    event.preventDefault(); // Prevent the form from submitting the traditional way

    const title = document.getElementById('title').value;
    const author = document.getElementById('author').value || null;

    // Disable the search button to prevent multiple submissions
    const searchButton = document.querySelector('button[type="submit"]');
    searchButton.disabled = true;

    // Loading options message
    document.getElementById('optionsList').innerHTML = '<li>Loading book options...</li>';

    // Send book title and author to the flask app
    fetch('https://audiobook-scraper-44c702a3d5e0.herokuapp.com/scrape', 
    {
        method: 'POST',
        credentials: 'include',
        headers: 
        {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({title: title, author: author})
    })
    
    // Handling response from the flask app
    .then(response => response.json())
    .then(data => {
        if (data.bookOptions) 
        {
            const bookOptions = data.bookOptions;
            const optionsList = document.getElementById('optionsList')
            optionsList.innerHTML = ''; // Clears any options from previous searches

            // Populate book options for user to choose from
            bookOptions.forEach((option, index) => {
                const listItem = document.createElement('li');
                listItem.innerHTML = `<button onclick="selectBook(${index + 1})">${option}</button>`;
                optionsList.appendChild(listItem);
            });
        } 
        else
        {
            alert(`No books found for ${title}`);
        }
        searchButton.disabled = false; // Re-enable the button after processing
    })
    .catch(error => 
    {
        console.error('Error:', error);
        alert('An error ocurred while searching for books.');
        searchButton.disabled = false;
    });
}

// Function to select book from options and trigger auidio scraping
function selectBook(selection) 
{
    fetch('https://audiobook-scraper-44c702a3d5e0.herokuapp.com/scrape/continue', 
    {
        method: 'POST',
        credentials: 'include',
        headers: 
        {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ selection: selection})
    })

    // Handling response from app
    .then(response => response.json())
    .then(data => 
    {
        if(data.audioFiles)
        {
            audioFiles = data.audioFiles;
            bookTitle = data.bookTitle.replace(/\s+/g, '_');  // Replace spaces with underscores for file names

            // Remove book list
            const bookList = document.getElementById('optionsList');
            optionsList.style.display = 'none';

            // Download button
            const downloadButton = document.getElementById('downloadButton');
            downloadButton.style.display = 'block';
            downloadButton.textContent = `Download ${bookTitle}`;

        }

        else 
        {
            alert('No audio files found')
        }
    })
    .catch(error => console.error('Error: ', error));
}

function downloadAudioFiles()
{
    // Trigger single request to download the ZIP
    const link = document.createElement('a');
    link.href = 'https://audiobook-scraper-44c702a3d5e0.herokuapp.com/download_all';
    link.download = `${bookTitle}_audiobook.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}