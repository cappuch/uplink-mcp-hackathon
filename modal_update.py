import modal
from utils.rss_parse import get_rss
from utils.mappings import mappings
from utils.news_content_strip import extract_main_content
from utils.models import embed_text, extract, bias
import requests
import time
import os
from dotenv import load_dotenv
load_dotenv()

app = modal.App("news-rss-scanner")

API_BASE_URL = "http://79.97.198.96:1337"
MAX_RETRIES = 3
RETRY_DELAY = 1

image = modal.Image.debian_slim().pip_install([
    "feedparser",
    "beautifulsoup4",
    "requests",
    "tqdm",
    "rss-parser",
    "huggingface_hub",
    "python-dotenv",
    "numpy"
]).copy_local_dir("./utils", "/root/utils")

def fetch_content(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching content from {url}: {e}")
        return ""

def find_record_by_url_api(url):
    """Check if a record exists using the API with retry logic"""
    headers = {"x-api-key": os.getenv('DB_API_KEY', '')}
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(f"{API_BASE_URL}/news/find", params={"url": url}, headers=headers, timeout=30)
            return response.status_code == 200
        except requests.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                print(f"Failed to check record existence after {MAX_RETRIES} attempts: {e}")
                return False
            time.sleep(RETRY_DELAY * (attempt + 1))
        except Exception as e:
            print(f"Unexpected error checking record: {e}")
            return False

def write_record_api(title, url, content, embedding, source, bias):
    """Write a record using the API with retry logic"""
    headers = {"x-api-key": os.getenv('DB_API_KEY', '')}
    data = {
        "title": title,
        "url": url,
        "content": content,
        "embedding": embedding,
        "source": source,
        "bias": bias
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(f"{API_BASE_URL}/news/write", json=data, headers=headers, timeout=30)
            if response.status_code == 200:
                return True
            else:
                print(f"API returned status {response.status_code}: {response.text}")
                return False
        except requests.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                print(f"Failed to write record after {MAX_RETRIES} attempts: {e}")
                return False
            print(f"Attempt {attempt + 1} failed, retrying in {RETRY_DELAY * (attempt + 1)}s: {e}")
            time.sleep(RETRY_DELAY * (attempt + 1))
        except Exception as e:
            print(f"Unexpected error writing to API: {e}")
            return False

def process_entry(entry, feed_name):
    try:
        url = str(entry.links[0].content if hasattr(entry.links[0], "content") else entry.links[0])
        if find_record_by_url_api(url):
            return
        content = fetch_content(url) if entry.links else ""
        if not content:
            print(f"No content found for {entry.title.content} in {feed_name}")
            return
        content = extract_main_content(content)
        content = extract(content)
        
        success = write_record_api(
            title=str(entry.title.content),
            url=url,
            content=str(content),
            embedding=embed_text(content),
            source=str(feed_name),
            bias=str(bias(content))
        )
        
        if success:
            print(f"Added new article: {entry.title.content} ({url})")
        else:
            print(f"Failed to write article: {entry.title.content} ({url})")
    except Exception as e:
        print(f"Error processing entry {entry.title.content} from {feed_name}: {e}")

def process_feed(feed_name, feeds):
    for feed_url in feeds:
        print(f"Processing feed: {feed_url}")
        rss = get_rss(feed_url)
        entries = rss.channel.items if rss else []
        for entry in entries:
            process_entry(entry, feed_name)

@app.function(
    image=image,
    schedule=modal.Period(minutes=15),
    secrets=[modal.Secret.from_name("HF_TOKEN")]
)
def scheduled_rss_scan():
    """Scheduled RSS scanning function"""
    print("Starting scheduled RSS scan...")
    
    for feed_name, feeds in mappings.items():
        process_feed(feed_name, feeds)
    
    print("Scheduled RSS scan complete.")

@app.function(image=image, secrets=[modal.Secret.from_name("HF_TOKEN")])
def manual_rss_scan():
    """Manually triggered RSS scanning function"""
    print("Starting manual RSS scan...")
    
    for feed_name, feeds in mappings.items():
        process_feed(feed_name, feeds)
    
    print("Manual RSS scan complete.")

# For local testing
if __name__ == "__main__":
    # Deploy the app
    app.deploy()