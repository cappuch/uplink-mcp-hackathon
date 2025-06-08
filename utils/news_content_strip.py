from bs4 import BeautifulSoup

def extract_main_content(html_content: str) -> str:
    soup = BeautifulSoup(html_content, 'html.parser')

    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'noscript', 'iframe', 'svg', 'button', 'input', 'figure', 'figcaption', 'advertisement', 'ads', 'meta', 'link']):
        tag.decompose()

    for el in soup.find_all(attrs={"class": lambda x: x and any(s in x.lower() for s in ['ad', 'promo', 'footer', 'header', 'sidebar', 'nav', 'cookie', 'banner', 'subscribe', 'newsletter', 'popup', 'modal'])}):
        el.decompose()
    for el in soup.find_all(attrs={"id": lambda x: x and any(s in x.lower() for s in ['ad', 'promo', 'footer', 'header', 'sidebar', 'nav', 'cookie', 'banner', 'subscribe', 'newsletter', 'popup', 'modal'])}):
        el.decompose()

    text = soup.get_text(separator=" ", strip=True)
    return text
