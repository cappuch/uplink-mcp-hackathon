# uplink - real-time information for llms
uplink brings real-time information to llms, as if the llm were trained 5 minutes ago
(this isnt a slop project)

public agent demo @[huggingface spaces](https://huggingface.co/spaces/Agents-MCP-Hackathon/uplink-mcp-demo-agent)

puiblic mcp demo @[huggingface spaces](https://huggingface.co/spaces/Agents-MCP-Hackathon/uplink-mcp)

### uplink features:
- backend (sqlite3 server running at home, where a modal cron job sends the new news articles back, and google-searching has caching (because, why not?))
- mcp (for your every day llms)
- agent for using this stuff

modal for scheduled scraping, mistral models behind the scenes, and huggingface inference api. db and fastapi server run on my pi at home.

![backend info](assets/info.png)

## what does it *exactly* do?

uplink acts as a mcp server/array of tools for language models to learn off of, from real time data sources like the news, and the web.
there's 3 endpoints that are public, which are:
- scrape webpage (turns a webpage into markdown)
- search (searches)
- search news (searches well, the news)

## what does it use (+ why)?
- conversion llm: `mistralai/Mistral-Small-3.1-24B-Instruct-2503`
    - practically uncensored compared to other llms. llama models would throw a hissy fit about political topics, which is all news is now. also has a HUGE context window.
- embedding model: `BAAI/bge-large-en-v1.5`
    - honestly, I don't know, felt like it.
- DB: `sqlite3`
    - easiest thing to use, and never changed
- search: google's custom search api with rotating keys
    - i'm broke, i can't afford requests
- agent model: `Qwen 2.5-72B-Instruct`
    - on nebius. works really well

(notice how i'm using mistral plz)

## security?
pretty pathetic to be honest, but it's a hackathon. trying to keep everything hidden away.

## i might want to deploy it for myself

alright so:
- (read the env example first)
1. install the deps (`pip install -r requirements.txt`, or `uv pip install -r requirements.txt` depending on the type of person you are)
2. do an initial scrape (`initial_scrape.py`) -  this will take a while.
3. run `db_server.py`, and update your .env to accomodate for this
4. then you can deploy `modal_update.py` that updates all the time every 5 minutes, or `update_hard.py` for a local update (also every 5 minutes)
5. then, `main_server.py`, and `mcp/app.py`. (make sure `db_server.py` is still running though!)

## i want my own news sources!
`utils/mappings.py` - mappings

`utils/feeds.py` - rss feeds

(read it and you'll understand how it works)

## contributing?
if you really *really* want to, fork and pr. no need to do so.

## license?
[dbad-derivative](license)