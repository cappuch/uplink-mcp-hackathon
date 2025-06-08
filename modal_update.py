import modal
import asyncio
from utils.rss_parse import get_rss
from utils.mappings import mappings
from utils.news_content_strip import extract_main_content
from utils.models import embed_text, extract, bias
import aiohttp

app = modal.App("news-rss-scanner")

API_BASE_URL = "http://localhost:8000"
MAX_RETRIES = 3
RETRY_DELAY = 1

image = modal.Image.debian_slim().pip_install([
    "aiohttp",
    "feedparser",
    "beautifulsoup4",
    "requests",
    "tqdm"
])

async def fetch_content(session, url):
    async with session.get(url, timeout=10) as resp:
        return await resp.text()

async def find_record_by_url_api(session, url):
    """Check if a record exists using the API with retry logic"""
    for attempt in range(MAX_RETRIES):
        try:
            async with session.get(f"{API_BASE_URL}/news/find", params={"url": url}, timeout=30) as resp:
                return resp.status == 200
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt == MAX_RETRIES - 1:
                print(f"Failed to check record existence after {MAX_RETRIES} attempts: {e}")
                return False
            await asyncio.sleep(RETRY_DELAY * (attempt + 1))
        except Exception as e:
            print(f"Unexpected error checking record: {e}")
            return False

async def write_record_api(session, title, url, content, embedding, source, bias):
    """Write a record using the API with retry logic"""
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
            async with session.post(f"{API_BASE_URL}/news/write", json=data, timeout=30) as resp:
                if resp.status == 200:
                    return True
                else:
                    error_text = await resp.text()
                    print(f"API returned status {resp.status}: {error_text}")
                    return False
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt == MAX_RETRIES - 1:
                print(f"Failed to write record after {MAX_RETRIES} attempts: {e}")
                return False
            print(f"Attempt {attempt + 1} failed, retrying in {RETRY_DELAY * (attempt + 1)}s: {e}")
            await asyncio.sleep(RETRY_DELAY * (attempt + 1))
        except Exception as e:
            print(f"Unexpected error writing to API: {e}")
            return False

async def process_entry(entry, feed_name, session, semaphore):
    async with semaphore:
        try:
            url = str(entry.links[0].content if hasattr(entry.links[0], "content") else entry.links[0])
            if await find_record_by_url_api(session, url):
                return
            content = await fetch_content(session, url) if entry.links else ""
            if not content:
                print(f"No content found for {entry.title.content} in {feed_name}")
                return
            content = extract_main_content(content)
            content = extract(content)
            
            success = await write_record_api(
                session,
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

async def process_feed(feed_name, feeds):
    semaphore = asyncio.Semaphore(4)
    async with aiohttp.ClientSession() as session:
        for feed_url in feeds:
            rss = get_rss(feed_url)
            entries = rss.channel.items if rss else []
            tasks = [
                process_entry(entry, feed_name, session, semaphore)
                for entry in entries
            ]
            await asyncio.gather(*tasks)

# Scheduled function that runs every 5 minutes
@app.function(
    image=image,
    schedule=modal.Period(minutes=5),
)
def scheduled_rss_scan():
    """Scheduled RSS scanning function"""
    print("Starting scheduled RSS scan...")
    
    async def scan():
        tasks = [process_feed(feed_name, feeds) for feed_name, feeds in mappings.items()]
        await asyncio.gather(*tasks)
        print("Scheduled RSS scan complete.")
    
    asyncio.run(scan())

# Optional: Manual trigger function
@app.function(image=image)
def manual_rss_scan():
    """Manually triggered RSS scanning function"""
    print("Starting manual RSS scan...")
    
    async def scan():
        tasks = [process_feed(feed_name, feeds) for feed_name, feeds in mappings.items()]
        await asyncio.gather(*tasks)
        print("Manual RSS scan complete.")
    
    asyncio.run(scan())

# For local testing
if __name__ == "__main__":
    # Deploy the app
    app.deploy()