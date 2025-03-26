import asyncio
import aiohttp
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import aiofiles
from tqdm.auto import tqdm


class AsyncDownloadProgress:
    def __init__(self, total_files):
        """
        Custom progress tracking for async downloads

        :param total_files: Total number of files to download
        """
        self.progress_bar = tqdm(
            total=total_files,
            desc="Downloading Files",
            unit="file",
            dynamic_ncols=True
        )
        self.completed = 0
        self.lock = asyncio.Lock()

    async def update(self, filename=None):
        """
        Thread-safe progress bar update

        :param filename: Optional filename for detailed logging
        """
        async with self.lock:
            self.completed += 1
            self.progress_bar.update(1)
            if filename:
                self.progress_bar.set_postfix_str(f"Last: {filename}")

    def close(self):
        """Close the progress bar"""
        self.progress_bar.close()


async def fetch_download_links(url):
    """Asynchronously fetch download links from the webpage."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            # Raise an exception for bad status codes
            response.raise_for_status()

            # Read the HTML content
            html = await response.text()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # Find all div elements with class 'bdpLink'
            download_links = soup.find_all('div', class_='bdpLink')

            # Extract href attributes from anchor tags within these divs
            links = [urljoin(url, link.find('a')['href'])
                     for link in download_links if link.find('a')]

            return links


async def download_file(session, url, output_dir, progress_tracker):
    """Asynchronously download a single file."""
    try:
        async with session.get(url) as response:
            # Raise an exception for bad status codes
            response.raise_for_status()

            # Extract filename from the URL
            filename = url.split('/')[-1]
            filepath = os.path.join(output_dir, filename)

            # Asynchronously write the file
            async with aiofiles.open(filepath, 'wb') as file:
                await file.write(await response.read())

            # Update progress
            await progress_tracker.update(filename)

            return filename

    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None


async def download_files(links, radar, year, month, day, max_concurrent=20):
    """Download multiple files concurrently with progress tracking."""
    # Create dynamic output directory name
    output_dir = f'{radar}_{year}_{month}_{day}'

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Create a progress tracker
    progress_tracker = AsyncDownloadProgress(len(links))

    # Create a semaphore to limit concurrent downloads
    sem = asyncio.Semaphore(max_concurrent)

    # Create a single session for all downloads
    async with aiohttp.ClientSession() as session:
        # Create download tasks with semaphore
        async def bounded_download(url):
            async with sem:
                return await download_file(session, url, output_dir, progress_tracker)

        # Use asyncio.gather to run downloads concurrently
        results = await asyncio.gather(*[bounded_download(link) for link in links])

        # Close the progress bar
        progress_tracker.close()

        # Return successful downloads
        return [r for r in results if r is not None]


async def main():
    # URL to scrape
    radar = input("Enter radar site (KHTX): ").strip()
    months = input("Enter month (03): ").strip()
    day = input("Enter day (15): ").strip()
    year = input("Enter year (2025): ").strip()

    url = f"https://www.ncdc.noaa.gov/nexradinv/bdp-download.jsp?id={radar}&yyyy={year}&mm={months}&dd={day}&product=AAL2"

    # Fetch download links
    download_links = await fetch_download_links(url)

    # Download files concurrently
    downloaded_files = await download_files(download_links, radar, year, months, day)

    print(f"Total files downloaded: {len(downloaded_files)}")
    print(f"Files saved in: {radar}_{year}_{months}_{day}")


# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())