import gradio as gr
from requests import get
import requests
def scrape_endpoint(
    url: str,
) -> dict:
    """
    Scrape a web page, extract main content, and summarize.
    Args:
        url: URL to scrape
    Returns:
        Extracted and summarized main content
    """
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200 or any(x in resp.text.lower() for x in ["cloudflare", "rate limit", "captcha"]):
            return {"error": "Blocked by site or rate limited.", "url": url}
        # Lazy import to avoid circular import issues
        from utils.news_content_strip import extract_main_content
        from utils.models import extract
        main_content = extract_main_content(resp.text)
        summary = extract(main_content)
        return {"url": url, "summary": summary}
    except Exception as e:
        return {"error": str(e), "url": url}
import os

base_url = os.getenv("base_url", "http://localhost:8001")
API_KEY = os.getenv("API_KEY", "hackathon-2025")

headers = {
    "X-API-Key": API_KEY
}


def search_endpoint(
        q: str,
        num: int = 5,
        start: int = 1,
        site: str = None,
        date_restrict: str = None
) -> dict:
    """
    Search the internet as if it were Google.

    Args:
        q: Search query
        num: Number of results to return (default 5) [5 is the maximum]
        start: Starting index for results (default 1)
        site: Restrict search to specific site (optional)
        date_restrict: Date restriction (e.g., 'd1', 'w1', 'm1') (optional)

    Returns:
        Search results as a dictionary
    """
    params = {
        "q": q,
        "num": num,
        "start": start,
        "site": site,
        "date_restrict": date_restrict
    }
    
    try:
        response = get(f"{base_url}/search", params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e), "query": q, "results": [], "count": 0}

def search_news_endpoint(
        q: str,
        num: int = 10,
) -> dict:
    """
    Search news articles, similar to Google News.

    Args:
        q: Search query
        num: Number of results to return (default 10)

    Returns:
        News search results as a dictionary
    """
    params = {
        "q": q,
        "num": num,
    }
    
    try:
        response = get(f"{base_url}/search/news", params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e), "query": q, "results": [], "count": 0}

with gr.Blocks(title="Uplink") as demo:
    gr.Markdown(
        """
        # 🌐 Uplink
        **A unified search interface for the web and news.**
        """
    )

    with gr.Tab("General Web Search"):
        with gr.Row():
            with gr.Column():
                query = gr.Textbox(label="Search Query", placeholder="Type your search here...")
                num_results = gr.Slider(minimum=1, maximum=5, value=5, label="Number of Results")
                start = gr.Slider(minimum=1, maximum=100, value=1, label="Starting Index")
                site = gr.Textbox(label="Restrict to Site (optional)", placeholder="e.g. wikipedia.org")
                date_restrict = gr.Dropdown(
                    choices=[None, "d1", "w1", "m1"],
                    value=None,
                    label="Date Restriction (optional)",
                    info="d1 = past day, w1 = past week, m1 = past month"
                )
                search_btn = gr.Button("🔍 Search")
            with gr.Column():
                output = gr.JSON(label="Results")

        search_btn.click(
            fn=search_endpoint,
            inputs=[query, num_results, start, site, date_restrict],
            outputs=output
        )

    with gr.Tab("Web Scrape"):
        with gr.Row():
            with gr.Column():
                scrape_url = gr.Textbox(label="URL to Scrape", placeholder="https://example.com")
                scrape_btn = gr.Button("🌐 Scrape")
            with gr.Column():
                scrape_output = gr.JSON(label="Scraped Content")

        scrape_btn.click(
            fn=scrape_endpoint,
            inputs=[scrape_url],
            outputs=scrape_output
        )

    with gr.Tab("News Search"):
        with gr.Row():
            with gr.Column():
                news_query = gr.Textbox(label="News Search Query", placeholder="Type your news topic...")
                news_num_results = gr.Slider(minimum=1, maximum=10, value=5, label="Number of Results")
                news_search_btn = gr.Button("📰 Search News")
            with gr.Column():
                news_output = gr.JSON(label="News Results")

        news_search_btn.click(
            fn=search_news_endpoint,
            inputs=[news_query, news_num_results],
            outputs=news_output
        )

    gr.Markdown(
        """
        ---
        <div align="center">
        <sub>Powered by Uplink &middot; Built with FastAPI + Gradio</sub>
        </div>
        """
    )

if __name__ == "__main__":
    demo.launch(mcp_server=True)