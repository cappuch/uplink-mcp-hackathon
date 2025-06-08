import asyncio
from utils.rss_parse import get_rss
from utils.db import write_record, find_record_by_url
from utils.mappings import mappings
from utils.news_content_strip import extract_main_content
from utils.models import embed_text, extract, bias
import aiohttp

SCAN_INTERVAL_SECONDS = 300

async def fetch_content(session, url):
    async with session.get(url, timeout=10) as resp:
        return await resp.text()

async def process_entry(entry, feed_name, session, semaphore):
    async with semaphore:
        try:
            url = str(entry.links[0].content if hasattr(entry.links[0], "content") else entry.links[0])
            if find_record_by_url(url):
                return
            content = await fetch_content(session, url) if entry.links else ""
            if not content:
                print(f"No content found for {entry.title.content} in {feed_name}")
                return
            content = extract_main_content(content)
            content = extract(content)
            write_record(
                title=str(entry.title.content),
                url=url,
                content=str(content),
                embedding=embed_text(content),
                source=str(feed_name),
                bias=str(bias(content))
            )
            print(f"Added new article: {entry.title.content} ({url})")
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

async def scan_loop():
    while True:
        print("Starting RSS scan...")
        tasks = [process_feed(feed_name, feeds) for feed_name, feeds in mappings.items()]
        await asyncio.gather(*tasks)
        print(f"Scan complete. Sleeping for {SCAN_INTERVAL_SECONDS} seconds.")
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)

if __name__ == "__main__":
    asyncio.run(scan_loop())