"""
Based on the Medium article by Fabian Bosler
https://towardsdatascience.com/image-scraping-with-python-a96feda8af2d
last accessed: 04.30.2022
"""
import hashlib
import io
import os
import requests
import signal
import time
from glob import glob
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

class timeout:
    """
    credit: https://stackoverflow.com/a/22348885
    """
    def __init__(self, seconds=1, error_message="Timeout"):
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)


def fetch_image_urls(
    query: str,
    max_links_to_fetch: int,
    wd: webdriver,
    sleep_between_interactions: int = 1,
):
    def scroll_to_end(wd):
        wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(sleep_between_interactions)

    search_url = "https://www.google.com/search?safe=off&site=&tbm=isch&source=hp&q={q}&oq={q}&gs_l=img"
    wd.get(search_url.format(q=query))

    image_urls = set()
    image_count = 0
    results_start = 0
    while image_count < max_links_to_fetch:
        scroll_to_end(wd)

        # Get all image thumbnail results
        # thumbnail_results = wd.find_elements_by_css_selector("img.Q4LuWd")
        thumbnail_results = wd.find_elements(by=By.CSS_SELECTOR, value="img.Q4LuWd")
        number_results = len(thumbnail_results)

        print(
            f"Found: {number_results} search results. Extracting links from {results_start}:{number_results}"
        )

        # Loop through image thumbnail identified
        for img in thumbnail_results[results_start:number_results]:
            # Try to click every thumbnail such that we can get the real image behind it.
            try:
                img.click()
                time.sleep(sleep_between_interactions)
            except Exception:
                continue

            # Extract image urls
            # actual_images = wd.find_elements_by_css_selector("img.n3VNCb")
            actual_images = wd.find_elements(by=By.CSS_SELECTOR, value="img.n3VNCb")

            for actual_image in actual_images:
                if actual_image.get_attribute(
                    "src"
                ) and "http" in actual_image.get_attribute("src"):
                    image_urls.add(actual_image.get_attribute("src"))

            image_count = len(image_urls)

            # If the number images found exceeds our `num_of_images`, end the seaerch.
            if len(image_urls) >= max_links_to_fetch:
                print(f"Found: {len(image_urls)} image links, done!")
                break
        else:
            # If we haven't found all the images we want, let's look for more.
            print("Found:", len(image_urls), "image links, looking for more ...")
            time.sleep(SLEEP_BEFORE_MORE)

            # Check for button signifying no more images.
            not_what_you_want_button = ""
            try:
                # not_what_you_want_button = wd.find_element_by_css_selector(".r0zKGf")
                not_what_you_want_button = wd.find_element(by=By.CSS_SELECTOR, value=".r0zKGf")
            except:
                pass

            # If there are no more images return.
            if not_what_you_want_button:
                print("No more images available.")
                return image_urls

            # If there is a "Load More" button, click it.
            # load_more_button = wd.find_element_by_css_selector(".mye4qd")
            load_more_button = wd.find_element(by=By.CSS_SELECTOR, value=".mye4qd")
            if load_more_button and not not_what_you_want_button:
                wd.execute_script("document.querySelector('.mye4qd').click();")

        # Move the result startpoint further down.
        results_start = len(thumbnail_results)

    return image_urls


def persist_image(folder_path: str, url: str):
    try:
        print("Getting image")
        # Download the image.  If timeout is exceeded, throw an error.
        with timeout(GET_IMAGE_TIMEOUT):
            image_content = requests.get(url).content

    except Exception as e:
        print(f"ERROR - Could not download {url} - {e}")

    try:
        # Convert the image into a bit stream, then save it.
        image_file = io.BytesIO(image_content)
        image = Image.open(image_file).convert("RGB")
        # Create a unique filepath from the contents of the image.
        file_path = os.path.join(
            folder_path, hashlib.sha1(image_content).hexdigest()[:10] + ".jpg"
        )
        with open(file_path, "wb") as f:
            image.save(f, "JPEG", quality=IMAGE_QUALITY)
        print(f"SUCCESS - saved {url} - as {file_path}")
    except Exception as e:
        print(f"ERROR - Could not save {url} - {e}")


def search_and_download(search_term: str, target_path="./images", number_images=5):
    options = Options()
    options.headless = True    
    target_folder = os.path.join(target_path, "_".join(search_term.lower().split(" ")))
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    with webdriver.Chrome(options=options) as wd:
        # Search for images URLs.
        res = fetch_image_urls(
            search_term,
            number_images,
            wd=wd,
            sleep_between_interactions=SLEEP_BETWEEN_INTERACTIONS,
        )

        # Download the images.
        if res is not None:
            for elem in res:
                persist_image(target_folder, elem)
        else:
            print(f"Failed to return links for term: {search_term}")


if __name__ == '__main__':
    # Parameters
    number_of_images = 400
    GET_IMAGE_TIMEOUT = 2
    SLEEP_BETWEEN_INTERACTIONS = 0.1
    SLEEP_BEFORE_MORE = 5
    IMAGE_QUALITY = 85

    output_path = "./images/"

    # Get terms already recorded
    dirs = glob(output_path + "*")
    dirs = [dir.split("/")[-1].replace("_", " ") for dir in dirs]

    search_terms = [
        "leo messi"
    ]

    # Exclude terms already stored
    search_terms = [term for term in search_terms if term not in dirs]

    for term in search_terms:
        search_and_download(term, output_path, number_of_images)